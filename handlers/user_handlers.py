import os
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, PreCheckoutQuery, CallbackQuery, ChatMemberUpdated, InlineKeyboardMarkup, \
    InlineKeyboardButton

from datetime import datetime, timedelta
from utils.constants import START_MESSAGE, PRICE
from keyboards import  generateKeyboard
from database import SessionLocal, UserPayments

from dotenv import load_dotenv
from utils.constants import ADMIN_ID
from utils.config import PAYMENTS_TOKEN


if not PAYMENTS_TOKEN:
    raise ValueError("Ошибка: PAYMENTS_TOKEN не найден. Проверьте .env файл.")

router = Router()

def is_subscription_active(user_id: int, group_id: int) -> bool:
    with SessionLocal() as db_session:
        # Проверяем наличие подписки пользователя для данной группы
        payment = db_session.query(UserPayments).filter_by(user_id=user_id, group_id=group_id).first()
        return payment is not None and payment.status == "оплачен"



@router.callback_query(F.data.startswith("group_"))
async def payment_handler(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    group_id = callback_query.data.split("_")[1]  # Извлекаем ID группы

    chat_member = await callback_query.bot.get_chat_member(group_id, user_id)

    # Проверяем статус пользователя в группе
    if chat_member.status == "kicked":
        # Снимаем бан, если пользователь заблокирован
        await callback_query.bot.unban_chat_member(group_id, user_id)
        await asyncio.sleep(1)

    if is_subscription_active(user_id, group_id):
        # Если подписка активна, создаем ссылку на группу
        expire_time = datetime.now() + timedelta(hours=24)
        new_invite_link = await callback_query.bot.create_chat_invite_link(
            group_id, expire_date=expire_time, member_limit=10
        )
        invite_url = new_invite_link.invite_link or "Ссылка не доступна."

        inline_kb_with_link = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Войти в группу', url=invite_url)],
            [InlineKeyboardButton(text='Закончил курс', callback_data='finished_course')]
        ])
        await callback_query.message.answer(
            "У вас уже есть активная подписка!",
            reply_markup=inline_kb_with_link
        )
    else:
        # Если подписки нет, отправляем счет на оплату
        await callback_query.message.bot.send_invoice(
            chat_id=callback_query.message.chat.id,
            title="Премиум доступ",
            description="Доступ к эксклюзивному контенту.",
            payload=f"premium_access_{group_id}",  # Включаем group_id в payload
            provider_token=PAYMENTS_TOKEN,
            currency="RUB",
            prices=PRICE
        )


@router.pre_checkout_query()
async def checkout_handler(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(lambda message: message.successful_payment is not None)
async def successful_payment_handler(message: Message):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload
    group_id = payload.split("_")[2]  # Извлекаем ID группы из payload

    with SessionLocal() as db_session:
        # Сохраняем информацию об оплате
        payment = UserPayments(
            user_id=user_id,
            group_id=group_id,  # Привязываем оплату к группе
            amount=message.successful_payment.total_amount / 100,
            currency=message.successful_payment.currency,
            payment_time=datetime.now(),
            invoice_payload=payload,
            status="оплачен",
            verified=True
        )
        db_session.add(payment)
        db_session.commit()

    try:
        # Снимаем бан, если пользователь был заблокирован в группе
        await message.bot.unban_chat_member(group_id, user_id)
    except Exception as e:
        print(f"Ошибка при снятии бана: {e}")

    # Создаем ссылку на группу
    expire_time = datetime.now() + timedelta(hours=24)
    new_invite_link = await message.bot.create_chat_invite_link(
        group_id, expire_date=expire_time, member_limit=10
    )
    invite_url = new_invite_link.invite_link

    inline_kb_with_link = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Войти в группу', url=invite_url)],
        [InlineKeyboardButton(text='Закончил курс', callback_data='finished_course')]
    ])
    await message.answer(
        "Оплата успешно завершена! Нажмите на кнопку ниже, чтобы присоединиться к группе.",
        reply_markup=inline_kb_with_link
    )


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
