
from aiogram import Router, F
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Command, ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import SessionLocal, Groups


admin = Router()
admin_id = 1446066933

class RegGroup(StatesGroup):
    name = State()
    price = State()
    group_id = State()

@admin.message(Command('admin'))
async def cmd_admin(message: Message):
    if message.from_user.id == admin_id and message.chat.type == "private":
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Добавить бота в группу", callback_data="add_bot_to_group")],
            [InlineKeyboardButton(text="Список групп", callback_data="all_groups")]
        ])

        await message.answer("Добро пожаловать в админ-панель. Выберите действие:", reply_markup=admin_kb)



@admin.callback_query(F.data == "add_bot_to_group")
async def reg_name(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(RegGroup.name)
    await callback_query.message.answer(f"Введите название группы:")

@admin.message(RegGroup.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(RegGroup.price)
    await message.answer("Введите цену для группы:")

group_data = {}

@admin.message(RegGroup.price)
async def reg_price(message: Message, state: FSMContext):
    data = await state.get_data()
    group_name = data.get("name")
    group_price = message.text

    group_data[message.from_user.id] = {
        "name": group_name,
        "price": group_price,
    }

    await state.set_state(RegGroup.group_id)
    bot_username = (await message.bot.get_me()).username
    invite_link = f"https://t.me/{bot_username}?startgroup=true"
    await message.answer(
        f"Теперь нужно добавить бота в группу в качестве администратора. Используйте эту ссылку: \n\n{invite_link}"
    )


@admin.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def bot_added(event: ChatMemberUpdated):
    if event.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
        if admin_id in group_data:
            group_info = group_data.pop(admin_id)
            group_name = group_info.get("name")
            group_price = group_info.get("price")
            group_id = event.chat.id

            db = SessionLocal()
            try:
                new_group = Groups(
                    group_name=group_name,
                    price=group_price,
                    group_id=group_id
                )
                db.add(new_group)
                db.commit()
                await event.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"Бот успешно добавлен в группу как администратор!\n"
                        f"Название группы: {group_name}\n"
                        f"Цена: {group_price}\n"
                        f"ID группы: {group_id}"
                    )
                )
            except Exception:
                db.rollback()
                await event.bot.send_message(
                    chat_id=admin_id,
                    text=f"Ошибка при сохранении данных группы. Попробуйте заново вести данные"
                )
                await event.bot.leave_chat(chat_id=group_id)

            finally:
                db.close()
        else:
            await event.bot.send_message(
                chat_id=admin_id,
                text="Ошибка: данные о группе не найдены. Попробуйте ещё раз."
            )
    else:
        await event.bot.send_message(
            chat_id=admin_id,
            text="Ошибка: бот был добавлен в группу, но не в качестве администратора. Проверьте настройки!"
        )



@admin.callback_query(F.data == "all_groups")
async def show_groups(callback_query: CallbackQuery):
    db = SessionLocal()
    try:
        # Получаем все группы из базы данных
        groups = db.query(Groups).all()
        if groups:
            # Формируем текст для отображения всех групп
            group_list = "\n".join(
                [
                    f"Название: {group.group_name}\nЦена: {group.price}\nID: {group.group_id}\n"
                    for group in groups
                ]
            )
            await callback_query.message.answer(f"Список групп:\n\n{group_list}")
        else:
            await callback_query.message.answer("В базе данных пока нет групп.")
    except Exception as e:
        await callback_query.message.answer(f"Ошибка при получении данных: {e}")
    finally:
        db.close()