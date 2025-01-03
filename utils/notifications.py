from aiogram.enums import parse_mode

from database import SessionLocal, UserPayments
from datetime import datetime, timedelta

async def notify_users_about_subscription(bot, admin_id):
    """Уведомляет пользователей об истечении подписки."""
    with SessionLocal() as db_session:
        now = datetime.now()
        tomorrow = now + timedelta(days=1)

        expiring_payments = db_session.query(UserPayments).filter(
            UserPayments.subscription_end_date <= tomorrow,
            UserPayments.subscription_end_date > now,
            UserPayments.status == "оплачен"
        ).all()

        admin_message = "🔔 Подписки следующих пользователей истекают завтра:\n"

        for payment in expiring_payments:
            try:
                # Уведомление пользователя
                await bot.send_message(
                    chat_id=payment.user_id,
                    text="⏳ Ваша подписка истекает завтра! Если вы не оплатите, вы будете удалены из группы. Связь @Abdulkhalim"
                )

                # Добавление информации для администратора с корректной ссылкой
                admin_message += (
                    f"<a href='tg://user?id={payment.user_id}'>Пользователь:</a> {payment.user_id}\nНомер телефона: {payment.phone_number}"
                )
            except Exception as e:
                # Если отправка сообщения пользователю не удалась, добавляем его номер телефона
                phone_number = payment.phone_number if payment.phone_number else "не указан"
                admin_message += (
                    f"❗ Не удалось уведомить пользователя с ID {payment.user_id}. "
                    f"📱 Номер телефона: {phone_number}\n"
                )
                print(f"Ошибка отправки сообщения пользователю {payment.user_id}: {e}")

        # Уведомление администратора одним сообщением
        if admin_message.strip() != "🔔 Подписки следующих пользователей истекают завтра:\n":
            await bot.send_message(
                chat_id=admin_id[0],
                text=admin_message,
                parse_mode=parse_mode.ParseMode.HTML
            )
