import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from handlers import router
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils.constants import ADMIN_ID
from utils.notifications import notify_users_about_subscription
from utils.subscription_manager import remove_expired_users


async def main():
    load_dotenv()
    bot = Bot(token=os.getenv("TOKEN"))
    scheduler = AsyncIOScheduler()
    # Настройка планировщика
    scheduler.add_job(notify_users_about_subscription, "interval", days=1, args=[bot, ADMIN_ID])
    scheduler.add_job(remove_expired_users, "interval", days=1, args=[bot])
    scheduler.start()
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')

