from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    delete,
    func,
    select,
    text,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import Settings


class Base(DeclarativeBase):
    pass


class MonitoredChat(Base):
    __tablename__ = "monitored_chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), default="")
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chat_type: Mapped[str] = mapped_column(String(32), default="unknown")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_message_id: Mapped[int] = mapped_column(Integer, default=0)


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)


class MonitorState(Base):
    __tablename__ = "monitor_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    is_running: Mapped[bool] = mapped_column(Boolean, default=False)


class BotSettings(Base):
    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    notify_mode: Mapped[str] = mapped_column(String(32), default="instant")
    poll_interval: Mapped[int] = mapped_column(Integer, default=10)
    scan_history_limit: Mapped[int] = mapped_column(Integer, default=100)
    scan_period_days: Mapped[int] = mapped_column(Integer, default=7)
    scan_mode: Mapped[str] = mapped_column(String(16), default="timeline")


class MatchRecord(Base):
    __tablename__ = "match_log"
    __table_args__ = (UniqueConstraint("chat_id", "message_id", name="uq_match_chat_message"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chat_title: Mapped[str] = mapped_column(String(512), default="")
    message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    text_preview: Mapped[str] = mapped_column(String(1000), default="")
    keywords: Mapped[str] = mapped_column(String(512), default="")
    message_link: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


engine = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str) -> None:
    global engine, async_session_factory
    engine = create_async_engine(database_url, echo=False)
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def _ensure_column(conn, table: str, column: str, ddl: str) -> None:
    columns = await conn.execute(text(f"PRAGMA table_info({table})"))
    column_names = {row[1] for row in columns.fetchall()}
    if column not in column_names:
        await conn.execute(text(ddl))


async def _ensure_match_dedup_index(conn) -> None:
    indexes = await conn.execute(text("PRAGMA index_list(match_log)"))
    if any(row[1] == "uq_match_chat_message" for row in indexes.fetchall()):
        return

    await conn.execute(
        text(
            "DELETE FROM match_log WHERE id NOT IN ("
            "SELECT MIN(id) FROM match_log GROUP BY chat_id, message_id"
            ")"
        )
    )
    await conn.execute(
        text(
            "CREATE UNIQUE INDEX uq_match_chat_message "
            "ON match_log(chat_id, message_id)"
        )
    )


async def create_tables(env_defaults: Settings | None = None) -> None:
    assert engine is not None
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if engine.dialect.name == "sqlite":
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA busy_timeout=30000"))
            await _ensure_column(
                conn,
                "monitored_chats",
                "chat_type",
                "ALTER TABLE monitored_chats ADD COLUMN chat_type VARCHAR(32) DEFAULT 'unknown'",
            )
            await _ensure_column(
                conn,
                "monitored_chats",
                "is_active",
                "ALTER TABLE monitored_chats ADD COLUMN is_active BOOLEAN DEFAULT 1",
            )
            await _ensure_match_dedup_index(conn)
            await _ensure_column(
                conn,
                "bot_settings",
                "scan_period_days",
                "ALTER TABLE bot_settings ADD COLUMN scan_period_days INTEGER DEFAULT 7",
            )
            await _ensure_column(
                conn,
                "bot_settings",
                "scan_mode",
                "ALTER TABLE bot_settings ADD COLUMN scan_mode VARCHAR(16) DEFAULT 'timeline'",
            )

    if env_defaults is not None:
        await ensure_bot_settings(env_defaults)


async def ensure_bot_settings(env_defaults: Settings) -> BotSettings:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        settings = await session.get(BotSettings, 1)
        if settings is None:
            settings = BotSettings(
                id=1,
                notify_mode="instant",
                poll_interval=env_defaults.poll_interval,
                scan_history_limit=env_defaults.scan_history_limit,
                scan_period_days=env_defaults.scan_period_days,
                scan_mode=env_defaults.scan_mode,
            )
            session.add(settings)
            await session.commit()
        return settings


async def get_bot_settings() -> BotSettings:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        settings = await session.get(BotSettings, 1)
        if settings is None:
            settings = BotSettings()
            session.add(settings)
            await session.commit()
        return settings


async def update_bot_settings(**kwargs) -> BotSettings:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        settings = await session.get(BotSettings, 1)
        if settings is None:
            settings = BotSettings(id=1)
            session.add(settings)
        for key, value in kwargs.items():
            setattr(settings, key, value)
        await session.commit()
        await session.refresh(settings)
        return settings


async def add_chat(
    chat_id: int,
    title: str,
    username: str | None,
    chat_type: str = "unknown",
) -> bool:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        existing = await session.scalar(
            select(MonitoredChat).where(MonitoredChat.chat_id == chat_id)
        )
        if existing:
            existing.title = title
            existing.username = username
            existing.chat_type = chat_type
            existing.is_active = True
            await session.commit()
            return False

        session.add(
            MonitoredChat(
                chat_id=chat_id,
                title=title,
                username=username,
                chat_type=chat_type,
                is_active=True,
            )
        )
        await session.commit()
        return True


async def remove_chat(chat_id: int) -> bool:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        result = await session.execute(
            delete(MonitoredChat).where(MonitoredChat.chat_id == chat_id)
        )
        await session.commit()
        return result.rowcount > 0


async def toggle_chat_active(chat_id: int) -> bool | None:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        chat = await session.scalar(
            select(MonitoredChat).where(MonitoredChat.chat_id == chat_id)
        )
        if chat is None:
            return None
        chat.is_active = not chat.is_active
        await session.commit()
        return chat.is_active


async def get_chat(chat_id: int) -> MonitoredChat | None:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        return await session.scalar(
            select(MonitoredChat).where(MonitoredChat.chat_id == chat_id)
        )


async def get_active_chat(chat_id: int) -> MonitoredChat | None:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        return await session.scalar(
            select(MonitoredChat).where(
                MonitoredChat.chat_id == chat_id,
                MonitoredChat.is_active.is_(True),
            )
        )


async def get_all_chats() -> list[MonitoredChat]:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        result = await session.scalars(select(MonitoredChat).order_by(MonitoredChat.title))
        return list(result.all())


async def get_active_chats() -> list[MonitoredChat]:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        result = await session.scalars(
            select(MonitoredChat)
            .where(MonitoredChat.is_active.is_(True))
            .order_by(MonitoredChat.title)
        )
        return list(result.all())


async def update_last_message_id(chat_id: int, message_id: int) -> None:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        chat = await session.scalar(
            select(MonitoredChat).where(MonitoredChat.chat_id == chat_id)
        )
        if chat and message_id > chat.last_message_id:
            chat.last_message_id = message_id
            await session.commit()


async def add_keyword(word: str) -> bool:
    assert async_session_factory is not None
    word = word.strip().lower()
    if not word:
        return False

    async with async_session_factory() as session:
        existing = await session.scalar(select(Keyword).where(Keyword.word == word))
        if existing:
            return False
        session.add(Keyword(word=word))
        await session.commit()
        return True


async def remove_keyword(word: str) -> bool:
    assert async_session_factory is not None
    word = word.strip().lower()
    async with async_session_factory() as session:
        result = await session.execute(delete(Keyword).where(Keyword.word == word))
        await session.commit()
        return result.rowcount > 0


async def get_all_keywords() -> list[str]:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        result = await session.scalars(select(Keyword).order_by(Keyword.word))
        return [k.word for k in result.all()]


async def get_stats() -> dict[str, int]:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        chats_count = await session.scalar(select(func.count()).select_from(MonitoredChat)) or 0
        active_chats = await session.scalar(
            select(func.count()).select_from(MonitoredChat).where(MonitoredChat.is_active.is_(True))
        ) or 0
        words_count = await session.scalar(select(func.count()).select_from(Keyword)) or 0
        matches_today = await session.scalar(
            select(func.count()).select_from(MatchRecord).where(
                MatchRecord.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            )
        ) or 0
        return {
            "chats": chats_count,
            "active_chats": active_chats,
            "words": words_count,
            "matches_today": matches_today,
        }


async def log_match(
    *,
    chat_id: int,
    chat_title: str,
    message_id: int,
    text_preview: str,
    keywords: str,
    message_link: str,
) -> bool:
    """Сохраняет совпадение. Возвращает True, если запись новая."""
    assert async_session_factory is not None
    async with async_session_factory() as session:
        session.add(
            MatchRecord(
                chat_id=chat_id,
                chat_title=chat_title,
                message_id=message_id,
                text_preview=text_preview[:1000],
                keywords=keywords[:512],
                message_link=message_link[:512],
            )
        )
        try:
            await session.commit()
            return True
        except IntegrityError:
            await session.rollback()
            return False


async def get_recent_matches(limit: int = 15) -> list[MatchRecord]:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        result = await session.scalars(
            select(MatchRecord).order_by(MatchRecord.created_at.desc()).limit(limit)
        )
        return list(result.all())


async def set_monitor_running(is_running: bool) -> None:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        state = await session.get(MonitorState, 1)
        if state is None:
            state = MonitorState(id=1, is_running=is_running)
            session.add(state)
        else:
            state.is_running = is_running
        await session.commit()


async def is_monitor_running() -> bool:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        state = await session.get(MonitorState, 1)
        return bool(state and state.is_running)
