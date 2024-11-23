from aiogram.fsm.state import StatesGroup, State


class RegGroup(StatesGroup):
    name = State()
    price = State()
    group_id = State()