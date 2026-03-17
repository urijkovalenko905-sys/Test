import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import config
from database.models import async_main
from handlers import education, admin, cool_features


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Инициализация БД (создаёт таблицы при первом запуске)
    await async_main()

    bot = Bot(token=config.bot_token.get_secret_value())

    # MemoryStorage — для FSM (рассылки, диалоги с AI)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров
    dp.include_router(education.router)
    dp.include_router(admin.router)
    dp.include_router(cool_features.router)

    print("✅ Бот успешно запущен!")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Бот остановлен.")
