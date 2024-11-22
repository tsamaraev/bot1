import  os
import asyncio
import  logging
from aiogram import Bot, Dispatcher

from handlers.user_handlers import user
from handlers.admin_habdlers import admin

async def main():

    bot = Bot(token='5818868065:AAEI0Lcvy0MmpVKdHWT_WUMnGAaExRJPas8')
    dp = Dispatcher()
    dp.include_routers(admin, user)
    await  dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')
