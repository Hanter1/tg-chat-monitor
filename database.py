from sqlalchemy import BigInteger, Boolean, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MonitoredChat(Base):
    __tablename__ = "monitored_chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), default="")
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_message_id: Mapped[int] = mapped_column(Integer, default=0)


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)


class MonitorState(Base):
    __tablename__ = "monitor_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    is_running: Mapped[bool] = mapped_column(Boolean, default=False)


engine = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str) -> None:
    global engine, async_session_factory
    engine = create_async_engine(database_url, echo=False)
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def create_tables() -> None:
    assert engine is not None
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def add_chat(chat_id: int, title: str, username: str | None) -> bool:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        existing = await session.scalar(
            select(MonitoredChat).where(MonitoredChat.chat_id == chat_id)
        )
        if existing:
            existing.title = title
            existing.username = username
            await session.commit()
            return False

        session.add(
            MonitoredChat(
                chat_id=chat_id,
                title=title,
                username=username,
            )
        )
        await session.commit()
        return True


async def get_all_chats() -> list[MonitoredChat]:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        result = await session.scalars(select(MonitoredChat))
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


async def get_all_keywords() -> list[str]:
    assert async_session_factory is not None
    async with async_session_factory() as session:
        result = await session.scalars(select(Keyword))
        return [k.word for k in result.all()]


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
