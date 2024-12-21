from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import SessionLocal, Groups, UserPayments


def getGroupes():
    db = SessionLocal()
    try:
        groups = db.query(Groups).all()
        return groups
    except Exception as e:
        print(e)
    finally:
        db.close()


def generateKeyboard() -> InlineKeyboardMarkup:
    groupes = getGroupes()  # Получаем список групп
    buttons = []

    if not groupes:
        # Если групп нет, добавляем одну кнопку с текстом "Нет доступных групп"
        buttons.append([InlineKeyboardButton(text="Нет доступных групп", callback_data="no_groups")])
    else:
        # Если группы есть, создаем кнопки
        for i in groupes:
            buttons.append([InlineKeyboardButton(
                text=i.group_name,  # Название группы
                callback_data=f"group_{i.group_id}"  # Используем ID группы в callback_data
            )])

    # Создаем объект клавиатуры с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def getmyGroupes(user_id):
    db = SessionLocal()
    try:
        buttons = []
        results = db.query(UserPayments, Groups.group_name, Groups.group_id).join(Groups,
                                                                                  Groups.group_id == UserPayments.group_id).filter(
            UserPayments.user_id == user_id).all()

        groupes = []
        for payment, group_name, group_id in results:
            groupes.append({
                "group_name": group_name,
                "group_id": group_id
            })

        print(groupes)
        if not groupes:
            # Если групп нет, добавляем одну кнопку с текстом "Нет доступных групп"
            buttons.append([InlineKeyboardButton(text="Нет доступных групп", callback_data="no_groups")])

        else:
            # Если группы есть, создаем кнопки
            for i in groupes:
                buttons.append([InlineKeyboardButton(
                    text=i["group_name"],  # Название группы
                    callback_data=f"group_{i['group_id']}"  # Используем ID группы в callback_data
                )])

        # Создаем объект клавиатуры с кнопками
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        return keyboard


    except Exception as e:
        print(e)
    finally:
        db.close()


def add_user_keyboard(user_id: int, group_id: int) -> InlineKeyboardMarkup:
    """
    Создает InlineKeyboardMarkup для добавления пользователя в группу.

    :param user_id: ID пользователя, которого нужно добавить.
    :param group_id: ID группы, куда нужно добавить пользователя.
    :return: InlineKeyboardMarkup с кнопкой добавления пользователя.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='✅ Добавить пользователя в группу',
                    callback_data=f"adduser_{user_id}_{group_id}"
                )
            ]
        ]
    )


def finish_course(user_id):
    db = SessionLocal()
    try:
        buttons = []
        results = db.query(UserPayments, Groups.group_name, Groups.group_id).join(Groups,
                                                                                  Groups.group_id == UserPayments.group_id).filter(
            UserPayments.user_id == user_id).all()

        groupes = []
        for payment, group_name, group_id in results:
            groupes.append({
                "group_name": group_name,
                "group_id": group_id
            })

        print(groupes)
        if not groupes:
            # Если групп нет, добавляем одну кнопку с текстом "Нет доступных групп"
            buttons.append([InlineKeyboardButton(text="Нет доступных групп", callback_data="no_groups")])

        else:
            # Если группы есть, создаем кнопки
            for i in groupes:
                buttons.append([InlineKeyboardButton(
                    text=i["group_name"],  # Название группы
                    callback_data=f"course_{i['group_id']}"  # Используем ID группы в callback_data
                )])

        # Создаем объект клавиатуры с кнопками
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        return keyboard


    except Exception as e:
        print(e)
    finally:
        db.close()


inline_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Все курсы', callback_data='all_courses')],
    [InlineKeyboardButton(text='Мои курсы', callback_data='my_courses')],
    [InlineKeyboardButton(text='Завершил курс', callback_data='finish_course')]
])


