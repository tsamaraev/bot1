from database import SessionLocal, UserPayments
from datetime import datetime

from utils.constants import ADMIN_ID


async def remove_expired_users(bot):
    """Удаляет пользователей с истекшей подпиской из группы."""
    with SessionLocal() as db_session:
        now = datetime.now()
        expired_users = db_session.query(UserPayments).filter(
            UserPayments.subscription_end_date <= now

        ).all()

        for payment in expired_users:
            try:
                # Проверяем статус пользователя в группе
                chat_member = await bot.get_chat_member(
                    chat_id=payment.group_id,
                    user_id=payment.user_id
                )

                # Если пользователь уже не состоит в группе, пропускаем его
                if chat_member.status in ["left", "kicked"]:
                    print(f"Пользователь {payment.user_id} уже не состоит в группе {payment.group_id}.")
                    continue

                # Удаляем пользователя из группы
                await bot.ban_chat_member(
                    chat_id=payment.group_id,
                    user_id=payment.user_id
                )

                # Опционально: удаляем запрет на повторное добавление
                await bot.unban_chat_member(
                    chat_id=payment.group_id,
                    user_id=payment.user_id
                )

                # Удаляем запись о пользователе из базы данных (опционально)
                db_session.delete(payment)
                db_session.commit()

                # Уведомление админу
                await bot.send_message(
                    chat_id=ADMIN_ID[0],
                    text=f"👤 Пользователь {payment.user_id} был удален из группы {payment.group_id} из-за неуплаты."
                )

            except Exception as e:
                print(f"Ошибка при блокировке пользователя {payment.user_id} в группе {payment.group_id}: {e}")
