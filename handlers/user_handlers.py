import asyncio

from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated, ReplyKeyboardMarkup, KeyboardButton
from states.state import CourseRegistration
from utils.constants import START_MESSAGE
from keyboards import generateKeyboard, inline_menu, getmyGroupes, finish_course, add_user_keyboard
from database import SessionLocal, UserPayments, Groups
from aiogram.utils.markdown import hlink

from utils.constants import ADMIN_ID

router = Router()

def is_subscription_active(user_id: int, group_id: int) -> bool:
    with SessionLocal() as db_session:
        payment = db_session.query(UserPayments).filter_by(user_id=user_id, group_id=group_id).first()
        return payment is not None and payment.status == "оплачен"


@router.callback_query(F.data.startswith("group_"))
async def check_course(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username or f"id: {user_id}"
    user_mention = hlink(username, f"tg://user?id={user_id}")
    db = SessionLocal()

    group_id = callback_query.data.split("_")[1]
    group = db.query(Groups).filter(Groups.group_id == group_id).first()

    # Проверка подписки перед запросом номера телефона
    if is_subscription_active(user_id, group_id):
        expire_time = datetime.now() + timedelta(hours=24)
        new_invite_link = await callback_query.bot.create_chat_invite_link(
            group_id, expire_date=expire_time, member_limit=10
        )
        invite_url = new_invite_link.invite_link
        await callback_query.message.answer(
            f"✅ У вас уже есть активная подписка на курс: {group.group_name}.\n"
            f"🔗 Ссылка на группу (срок действия 24 часа): \n{invite_url}",
        )
        return

    # Сохраняем данные в FSM
    await state.update_data(group_id=group_id, group_name=group.group_name)

    # Запрашиваем номер телефона
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📲 Отправить номер телефона", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await callback_query.message.answer(
        "📞 Пожалуйста, отправьте ваш номер телефона, используя кнопку ниже.",
        reply_markup=keyboard
    )
    await state.set_state(CourseRegistration.waiting_for_phone)

# 📌 Обработка номера телефона
@router.message(CourseRegistration.waiting_for_phone, F.contact)
async def process_phone_number(message: Message, state: FSMContext):
    user_id = message.from_user.id
    phone_number = message.contact.phone_number

    # Получаем данные из состояния
    user_data = await state.get_data()
    group_name = user_data['group_name']

    with SessionLocal() as db:
        # Проверка существования группы
        group = db.query(Groups).filter(Groups.group_name == group_name).first()
        if not group:
            await message.answer("❌ Группа не найдена.")
            return

        # Проверка на существование пользователя
        existing_payment = db.query(UserPayments).filter_by(user_id=user_id, group_id=group.group_id).first()
        if existing_payment:
            await message.answer("✅ Вы уже отправили запрос на вступление в эту группу.")
            return

        # Добавляем запись в базу данных с предварительным статусом
        payment = UserPayments(
            user_id=user_id,
            group_id=group.group_id,
            phone_number=phone_number,  # Сохраняем номер телефона
            status="ожидает подтверждения",
        )
        db.add(payment)
        db.commit()

        # Уведомляем администратора
        user_mention = hlink(message.from_user.username or f"id: {user_id}", f"tg://user?id={user_id}")
        await message.bot.send_message(
            chat_id=ADMIN_ID[0],
            text=(
                f"🔔 Запрос на вступление в группу:\n"
                f"👤 Пользователь: {user_mention}\n"
                f"📚 Курс: {group_name}\n"
                f"📱 Номер телефона: {phone_number}"
            ),
            reply_markup=add_user_keyboard(user_id, group.group_id),
            parse_mode="HTML"
        )
        await message.answer("✅ Ваш номер отправлен администратору. Ожидайте подтверждения!")
        await state.clear()

@router.callback_query(F.data == "finished_course")
async def finished_course_handler(callback_query: CallbackQuery):
    await callback_query.answer("")
    await callback_query.message.bot.send_message(
         ADMIN_ID[0],
        f"Пользователь {callback_query.from_user.username or callback_query.from_user.id} завершил курс."
    )


@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.chat.type == 'private':
        await message.answer(START_MESSAGE, reply_markup=generateKeyboard())


@router.chat_member()
async def chat_member_status(event: ChatMemberUpdated):
    user_id = event.new_chat_member.user.id
    group_id = event.chat.id  # Идентификатор группы

    # Проверяем, есть ли активная подписка для этой группы
    if not is_subscription_active(user_id, group_id):
        try:
            # Баним пользователя в этой группе
            await event.bot.ban_chat_member(group_id, user_id)
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Ошибка при блокировке пользователя {user_id} в группе {group_id}: {e}")


@router.message(Command("menu"))
async def cmd_start(message: Message):
    if message.chat.type == 'private':
        await message.answer("Выберите опцию:", reply_markup=inline_menu)


@router.callback_query(F.data == "all_courses")
async def finished_course_handler(callback_query: CallbackQuery):
    await callback_query.message.answer("Все курсы:", reply_markup=generateKeyboard())


@router.callback_query(F.data == "my_courses")
async def finished_course_handler(callback_query: CallbackQuery):
    await callback_query.message.answer("Мои курсы:", reply_markup=getmyGroupes(callback_query.from_user.id))


@router.callback_query(F.data == "finish_course")
async def finished_course_handler(callback_query: CallbackQuery):
    await callback_query.message.answer("Выберите курс который вы завершили:", reply_markup=finish_course(callback_query.from_user.id))


@router.callback_query(F.data.startswith("course_"))
async def payment_handler(callback_query: CallbackQuery):
    group_id = callback_query.data.split("_")[1]  # Извлекаем ID группы
    db = SessionLocal()
    group = db.query(Groups).filter(Groups.group_id == group_id).first()
    try:
        user_id = callback_query.from_user.id
        username = callback_query.from_user.username or f"id: {user_id}"
        user_mention = hlink(username, f"tg://user?id={user_id}")

        await callback_query.bot.send_message(
            chat_id=ADMIN_ID[0],
            text=(
                f"Пользователь {user_mention} завершил курс "
                f"{group.group_name}"
            ),
            parse_mode="HTML"
        )
        await callback_query.message.answer("Мы отправили ваше сообщение.")
    except Exception as e:
        await callback_query.message.answer(
            "Произошла ошибка при отправке сообщения администратору."
        )
        print(f"Ошибка: {e}")

