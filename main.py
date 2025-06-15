from bot import bot, dp
from handlers import register_handlers
from utils.logger import logger
from utils.db import init_db

async def main():
    init_db()
    register_handlers(dp)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
