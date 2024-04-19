import asyncio
import aiosqlite
import logging
import shutil
from bot.handlers.user_handlers import user_router
from bot.config import BotConfig
from bot.bot_instance import dp, bot
from datetime import datetime

# logging.basicConfig(filename='logger.txt', level=logging.ERROR,
#                     format="%(asctime)s:%(levelname)s:%(message)s")


async def get_db_connection():
    try:
        conn = await aiosqlite.connect("database.db")
        return conn
    except Exception as e:
        logging.error(f"Error at the connection to the database: {e}")
        raise


async def backup_database():
    while True:
        try:
            shutil.copy("database.db", "database_backup.db")
            logging.info(
                f"The database has been successfully backed up at {datetime.now()}"
            )
        except Exception as e:
            logging.error(f"Error at the back up of database: {e}")
        await asyncio.sleep(3600)  # 1 hour


def register_routers() -> None:
    dp.include_router(user_router)


async def main() -> None:
    db_connection = await get_db_connection()

    config = BotConfig(
        token=bot.token,
        db_connection=db_connection,
        user_id_list=[],
    )

    dp["config"] = config

    register_routers()

    # Start the backup task
    backup_task = asyncio.create_task(backup_database())

    try:
        await dp.start_polling(bot, skip_updates=False)
    finally:
        backup_task.cancel()
        await db_connection.close()


if __name__ == "__main__":
    asyncio.run(main())
