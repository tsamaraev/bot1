from aiogram.fsm.state import StatesGroup, State


class RegGroup(StatesGroup):
    name = State()
    price = State()
    group_id = State()


class CourseRegistration(StatesGroup):
    waiting_for_phone = State()
    waiting_for_confirmation = State()
