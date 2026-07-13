from aiogram.fsm.state import State, StatesGroup


class AddWordState(StatesGroup):
    waiting_word = State()
