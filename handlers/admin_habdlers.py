from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import Command, ChatMemberUpdatedFilter, JOIN_TRANSITION, IS_ADMIN
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import SessionLocal, Groups, UserPayments
from utils.constants import ADMIN_ID
from states.state import RegGroup
from keyboards import backToAdminMenu, makeMainAdminMenu, makeAdminSubscriptionMenu

router = Router()


@router.message(Command('admin'))
async def cmd_admin(message: Message):
    if message.from_user.id in ADMIN_ID and message.chat.type == "private":
        await message.answer("Добро пожаловать в админ-панель. Выберите действие:", reply_markup=makeMainAdminMenu())


@router.callback_query(F.data.startswith("adduser_"))
async def add_user_group(callback_query: CallbackQuery):
    """Добавление пользователя в закрытую группу с подтверждением подписки."""
    user_id = int(callback_query.data.split("_")[1])
    group_id = callback_query.data.split("_")[2]

    with SessionLocal() as db_session:
        try:
            # Проверка существования записи о платеже
            payment = db_session.query(UserPayments).filter_by(user_id=user_id, group_id=group_id).first()
            if not payment:
                await callback_query.message.answer("❌ Пользователь не найден в базе данных.")
                return

            # Обновляем статус на "оплачен" и дату окончания подписки
            subscription_end_date = datetime.now() + timedelta(days=30)  # Подписка на 30 дней
            payment.status = "оплачен"
            payment.subscription_end_date = subscription_end_date
            db_session.commit()

            # Создаем ссылку на приглашение в группу
            expire_time = datetime.now() + timedelta(hours=24)  # Срок действия ссылки 24 часа
            try:
                new_invite_link = await callback_query.bot.create_chat_invite_link(
                    group_id, expire_date=expire_time, member_limit=1
                )
                invite_url = new_invite_link.invite_link

                # Отправляем уведомление пользователю
                await callback_query.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"✅ Вы успешно добавлены в группу \"{group_id}\". "
                        f"Ваша подписка активна до {subscription_end_date.strftime('%d.%m.%Y %H:%M')}.\n"
                        f"Перейдите по ссылке, чтобы присоединиться: {invite_url}"
                    )
                )
            except Exception:
                # Если `user_id` некорректный, уведомляем администратора с номером телефона
                await callback_query.message.answer(
                    text=(
                        f"❗ Не удалось отправить сообщение пользователю.\n"
                        f"📱 Номер телефона: {payment.phone_number}"
                    )
                )

            # Уведомляем администратора
            await callback_query.message.answer(
                text=f"✅ Пользователь {user_id} успешно добавлен в группу."
            )

        except Exception as e:
            db_session.rollback()
            await callback_query.message.answer(
                text=f"❌ Произошла ошибка при добавлении пользователя: {str(e)}"
            )
        finally:
            db_session.close()


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


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def bot_added(event: ChatMemberUpdated):
    if event.from_user.id in ADMIN_ID:
        group_name = group_data.get(event.from_user.id, {}).get('name')
        group_id = event.chat.id

        db = SessionLocal()
        try:
            # Проверяем, есть ли уже эта группа в базе
            existing_group = db.query(Groups).filter_by(group_id=group_id).first()
            if existing_group:
                await event.bot.send_message(
                    chat_id=ADMIN_ID[0],
                    text=f"⚠️ Бот уже добавлен в группу '{existing_group.group_name}' (ID: {group_id})."
                )
                return  # Выход из функции, чтобы не вставлять дубликат

            # Если группа новая, добавляем её
            new_group = Groups(
                group_name=group_name,
                group_id=group_id
            )
            db.add(new_group)
            db.commit()
            await event.bot.send_message(
                chat_id=ADMIN_ID[0],
                text=(
                    f"✅ Бот успешно добавлен в группу!\n"
                    f"Название группы: {group_name}\n"
                )
            )
        except Exception as e:
            db.rollback()
            await event.bot.send_message(
                chat_id=ADMIN_ID[0],
                text=f"❌ Ошибка при сохранении данных группы: {str(e)}"
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
            await callback_query.message.edit_text(
                text=f"Список групп:\n\n{group_list}",
                reply_markup=backToAdminMenu()
            )
        else:
            await callback_query.message.answer("В базе данных пока нет групп.")
    except Exception as e:
        await callback_query.message.answer(f"Ошибка при получении данных: {e}")
    finally:
        db.close()


@router.callback_query(F.data == 'backToAdminMenu')
async def adminMenu(callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        text=f"Добро пожаловать в админ-панель. Выберите действие:",
        reply_markup=makeMainAdminMenu()
    )


@router.callback_query(F.data.startswith("extend_subscription_"))
async def extend_subscription(callback_query: CallbackQuery):
    user_id = int(callback_query.data.split("_")[2])

    with SessionLocal() as db_session:
        payment = db_session.query(UserPayments).filter_by(user_id=user_id).first()

        if payment:
            payment.subscription_end_date += timedelta(days=30)
            db_session.commit()

            await callback_query.message.edit_text(
                text=f"✅ Подписка пользователя {user_id} продлена на месяц."
            )
            await callback_query.bot.send_message(
                chat_id=user_id,
                text="✅ Ваша подписка была продлена администратором на 1 месяц!"
            )
        else:
            await callback_query.message.edit_text("❌ Пользователь не найден.")


@router.callback_query(F.data == "manage_subscriptions")
async def manage_subscriptions(callback_query: CallbackQuery):
    with SessionLocal() as db_session:
        now = datetime.now()
        expiring_users = db_session.query(UserPayments).filter(
            UserPayments.subscription_end_date <= now + timedelta(days=7),
            UserPayments.status == "оплачен"
        ).all()
        print(expiring_users)
        if expiring_users:
            await callback_query.message.edit_text(
                text="📋 Список пользователей с истекающими подписками:",
                reply_markup=makeAdminSubscriptionMenu(expiring_users)
            )
        else:
            await callback_query.message.edit_text("ℹ️ Нет пользователей с истекающими подписками.")