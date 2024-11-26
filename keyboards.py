from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import SessionLocal, Groups


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


