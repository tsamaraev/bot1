import os
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, PreCheckoutQuery, CallbackQuery, ChatMemberUpdated, InlineKeyboardMarkup, \
    InlineKeyboardButton
from dotenv import load_dotenv
from datetime import datetime, timedelta
from utils.constants import START_MESSAGE, PRICE
from keyboards import inline_kb
from database import SessionLocal, UserPayments
import asyncio

load_dotenv()
payments_token = os.getenv("PAYMENTS_TOKEN")
if not payments_token:
    raise ValueError("Ошибка: PAYMENTS_TOKEN не найден. Проверьте .env файл.")

user = Router()
admin_id = 1446066933
group_chat_id = -1002198089460


def is_subscription_active(user_id: int) -> bool:
    with SessionLocal() as db_session:
        payment = db_session.query(UserPayments).filter_by(user_id=user_id).first()
        return payment is not None


@user.callback_query(F.data == "buy")
async def payment_handler(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    chat_member = await callback_query.bot.get_chat_member(group_chat_id, user_id)
    print(chat_member)
    if chat_member.status == 'kicked':
        await callback_query.bot.unban_chat_member(group_chat_id, user_id)
        await asyncio.sleep(1)

    print(chat_member)

    if is_subscription_active(user_id):
        expire_time = datetime.now() + timedelta(hours=24)
        new_invite_link = await callback_query.bot.create_chat_invite_link(group_chat_id, expire_date=expire_time,
                                                                           member_limit=10)
        invite_url = new_invite_link.invite_link or "Ссылка не доступна."

        inline_kb_with_link = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Войти в канал', url=invite_url)],
            [InlineKeyboardButton(text='Закончил курс', callback_data='finished_course')]
        ])
        await callback_query.message.answer("У вас уже есть активная подписка!", reply_markup=inline_kb_with_link)
    else:
        await callback_query.message.bot.send_invoice(
            chat_id=callback_query.message.chat.id,
            title="Премиум доступ",
            description="Доступ к эксклюзивному контенту.",
            payload="premium-access",
            provider_token=payments_token,
            currency="RUB",
            prices=PRICE
        )


@user.pre_checkout_query()
async def checkout_handler(query: PreCheckoutQuery):
    await query.answer(ok=True)


@user.message(lambda message: message.successful_payment is not None)
async def successful_payment_handler(message: Message):
    user_id = message.from_user.id
    chat_member = await message.bot.get_chat_member(group_chat_id, user_id)
    print(chat_member)

    with SessionLocal() as db_session:
        payment = db_session.query(UserPayments).filter_by(user_id=user_id).first()
        if payment:
            payment.status = "оплачен"
            payment.verified = True
            payment.amount = message.successful_payment.total_amount / 100
            payment.currency = message.successful_payment.currency
            payment.payment_time = datetime.now()
            payment.invoice_payload = message.successful_payment.invoice_payload
        else:
            payment = UserPayments(
                user_id=user_id,
                amount=message.successful_payment.total_amount / 100,
                currency=message.successful_payment.currency,
                payment_time=datetime.now(),
                invoice_payload=message.successful_payment.invoice_payload,
                status="оплачен",
                verified=True
            )
            db_session.add(payment)
        db_session.commit()

    expire_time = datetime.now() + timedelta(hours=24)
    new_invite_link = await message.bot.create_chat_invite_link(
        group_chat_id, expire_date=expire_time, member_limit=10
    )
    invite_url = new_invite_link.invite_link

    inline_kb_with_link = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Войти в канал', url=invite_url)],
        [InlineKeyboardButton(text='Закончил курс', callback_data='finished_course')]
    ])
    await message.answer(
        "Оплата успешно завершена! Нажмите на кнопку ниже, чтобы присоединиться к группе.",
        reply_markup=inline_kb_with_link
    )


@user.callback_query(F.data == "finished_course")
async def finished_course_handler(callback_query: CallbackQuery):
    await callback_query.answer("К")
    await callback_query.message.bot.send_message(
        admin_id,
        f"Пользователь {callback_query.from_user.username or callback_query.from_user.id} завершил курс."
    )


@user.message(CommandStart)
async def cmd_start(message: Message):
    if message.chat.type == 'private':
        await message.answer(START_MESSAGE, reply_markup=inline_kb)

@user.chat_member()
async def chat_member_status(event: ChatMemberUpdated):
    user_id = event.new_chat_member.user.id
    chat = event.chat.get_member(user_id=user_id)
    print(user_id, chat)
    if not is_subscription_active(user_id):
        await event.bot.ban_chat_member(group_chat_id, user_id)
        await asyncio.sleep(1)
        print("Бан")
    else:
        print("Есть подписка")
