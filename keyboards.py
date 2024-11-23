from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import SessionLocal, Groups


# def
# db = SessionLocal()
# try:
#     groups = db.query(Groups).all()
#     for group in groups:
#         print(group.group_name)
# except Exception as e:
#     print(e)
# finally:
#     db.close()


inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Канал 1', callback_data='buy')],
])

