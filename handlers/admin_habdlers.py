from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import Command, ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import SessionLocal, Groups, UserPayments
from utils.constants import ADMIN_ID
from states.state import RegGroup



router = Router()


@router.message(Command('admin'))
async def cmd_admin(message: Message):
    if message.from_user.id in ADMIN_ID and message.chat.type == "private":
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Добавить бота в группу", callback_data="add_bot_to_group")],
            [InlineKeyboardButton(text="Список групп", callback_data="all_groups")]
        ])

        await message.answer("Добро пожаловать в админ-панель. Выберите действие:", reply_markup=admin_kb)


@router.callback_query(F.data.startswith("adduser_"))
async def add_user_group(callback_query: CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    group_id = callback_query.data.split("_")[2]

    with SessionLocal() as db_session:
        # Проверка на существование пользователя в группе
        existing_payment = db_session.query(UserPayments).filter_by(
            user_id=user_id,
            group_id=group_id
        ).first()

        if existing_payment:
            await callback_query.bot.send_message(
                chat_id=ADMIN_ID[0],
                text="✅ Вы уже добавили его в эту группу."
            )
            return  # Прекращаем выполнение, если пользователь уже есть в БД

        # Если записи нет, добавляем пользователя
        payment = UserPayments(
            user_id=user_id,
            group_id=group_id,
            status="оплачен",
            verified=True
        )
        db_session.add(payment)
        db_session.commit()
        expire_time = datetime.now() + timedelta(hours=24)
        new_invite_link = await callback_query.bot.create_chat_invite_link(
            group_id, expire_date=expire_time, member_limit=10
        )
        invite_url = new_invite_link.invite_link
        await callback_query.bot.send_message(
            chat_id=user_id,
            text=f"✅ Вы успешно добавлены в группу. \nПерейдите по ссылке: {invite_url}"
        )


@router.callback_query(F.data == "add_bot_to_group")
async def reg_name(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(RegGroup.name)
    await callback_query.message.answer(f"Введите название группы:")

group_data = {}

@router.message(RegGroup.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)

    data = await state.get_data()
    group_name = data.get("name")
    group_data[message.from_user.id] = {
        "name": group_name,
    }
    await state.set_state(RegGroup.group_id)
    bot_username = (await message.bot.get_me()).username
    invite_link = f"https://t.me/{bot_username}?startgroup=true"
    await message.answer(
        f"Теперь нужно добавить бота в группу в качестве администратора. Используйте эту ссылку: \n\n{invite_link}"
    )




# @router.message(RegGroup.group_id)
# async def reg_price(message: Message, state: FSMContext):
#     data = await state.get_data()
#     group_name = data.get("name")
#     group_price = message.text
#
#     group_data[message.from_user.id] = {
#         "name": group_name,
#         "price": group_price,
#     }
#
#     await state.set_state(RegGroup.group_id)
#     bot_username = (await message.bot.get_me()).username
#     invite_link = f"https://t.me/{bot_username}?startgroup=true"
#     await message.answer(
#         f"Теперь нужно добавить бота в группу в качестве администратора. Используйте эту ссылку: \n\n{invite_link}"
#     )


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def bot_added(event: ChatMemberUpdated):
    if event.from_user.id in ADMIN_ID:
        print(group_data)
        group_name = group_data.get(event.from_user.id).get('name')
        group_id = event.chat.id

        db = SessionLocal()
        try:
            new_group = Groups(
                group_name=group_name,
                group_id=group_id
            )
            db.add(new_group)
            db.commit()
            await event.bot.send_message(
                chat_id=ADMIN_ID[0],
                text=(
                    f"Бот успешно добавлен в группу как администратор!\n"
                    f"Название группы: {group_name}\n"
                )
            )
        except Exception:
            db.rollback()
            await event.bot.send_message(
                chat_id=ADMIN_ID[0],
                text=f"Ошибка при сохранении данных группы. Попробуйте заново вести данные"
            )
            await event.bot.leave_chat(chat_id=group_id)

        finally:
            db.close()


@router.callback_query(F.data == "all_groups")
async def show_groups(callback_query: CallbackQuery):
    db = SessionLocal()
    try:
        # Получаем все группы из базы данных
        groups = db.query(Groups).all()
        if groups:
            # Формируем текст для отображения всех групп
            group_list = "\n".join(
                [
                    f"Название: {group.group_name}\nID: {group.group_id}\n"
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
