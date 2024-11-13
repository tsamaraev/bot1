import  os
import asyncio
import  logging
from aiogram import Bot, Dispatcher
from  dotenv import  load_dotenv

from handlers.user_handlers import user

async def main():
    load_dotenv()
    bot = Bot(token=os.getenv('TOKEN'))
    dp = Dispatcher()
    dp.include_router(user)
    await  dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')
