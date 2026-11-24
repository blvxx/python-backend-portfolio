"""Application entry point supporting polling and horizontally-scalable webhooks."""

import asyncio  # noqa: I001
import logging
import signal
from datetime import timedelta

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web
from redis.asyncio import Redis

from src.application.enquiries import EnquiryService
from src.application.notifications import (
    NotificationOutboxDispatcher,
    run_outbox_worker,
)
from src.config import Settings
from src.database import Database
from src.handlers import router
from src.infrastructure.telegram_notifications import TelegramLeadNotificationSender
from src.observability import create_observability_app
from src.postgres_database import PostgresDatabase


logger = logging.getLogger(__name__)


def _build_database(settings: Settings) -> Database | PostgresDatabase:
    if settings.database_url:
        if not settings.database_url.startswith(("postgres://", "postgresql://")):
            raise ValueError("DATABASE_URL must use PostgreSQL")
        return PostgresDatabase(settings.database_url)
    return Database(settings.database_path)


def _install_shutdown_signals(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, stop_event.set)
        except NotImplementedError:
            logger.warning("Signal handler is unavailable", extra={"signal": signum.name})


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    settings = Settings.from_env()
    database = _build_database(settings)
    await database.initialize()

    redis_client: Redis | None = None
    if settings.redis_url:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        storage = RedisStorage(
            redis=redis_client,
            state_ttl=timedelta(seconds=settings.fsm_state_ttl_seconds),
            data_ttl=timedelta(seconds=settings.fsm_state_ttl_seconds),
        )
    else:
        if settings.bot_mode == "webhook":
            raise RuntimeError("Redis is mandatory in webhook/multi-replica mode")
        logger.warning(
            "REDIS_URL is not configured; FSM state is process-local and will be lost on restart"
        )
        storage = MemoryStorage()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(
        storage=storage,
        events_isolation=storage.create_isolation() if redis_client else None,
    )
    enquiry_service = EnquiryService(database)
    notification_dispatcher = NotificationOutboxDispatcher(
        database,
        TelegramLeadNotificationSender(bot),
    )
    dispatcher["db"] = database
    dispatcher["enquiry_service"] = enquiry_service
    dispatcher["settings"] = settings
    dispatcher.include_router(router)

    stop_event = asyncio.Event()
    worker_task = asyncio.create_task(
        run_outbox_worker(notification_dispatcher, stop_event)
    )
    app = create_observability_app(database, redis_client)
    if settings.bot_mode == "webhook":
        assert settings.webhook_secret is not None
        assert settings.webhook_base_url is not None
        SimpleRequestHandler(
            dispatcher=dispatcher,
            bot=bot,
            secret_token=settings.webhook_secret,
        ).register(app, path=settings.webhook_path)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(
        runner,
        host=settings.web_server_host,
        port=settings.web_server_port,
    )

    try:
        await site.start()
        logger.info(
            "Observability server started",
            extra={"host": settings.web_server_host, "port": settings.web_server_port},
        )

        if settings.bot_mode == "webhook":
            await dispatcher.emit_startup(bot=bot)
            webhook_url = f"{settings.webhook_base_url}{settings.webhook_path}"
            await bot.set_webhook(
                webhook_url,
                secret_token=settings.webhook_secret,
                allowed_updates=dispatcher.resolve_used_update_types(),
            )
            logger.info("Telegram webhook registered")
            _install_shutdown_signals(stop_event)
            await stop_event.wait()
        else:
            # Long polling and webhook delivery must never run simultaneously.
            await bot.delete_webhook(drop_pending_updates=False)
            _install_shutdown_signals(stop_event)
            polling_task = asyncio.create_task(
                dispatcher.start_polling(
                    bot,
                    allowed_updates=dispatcher.resolve_used_update_types(),
                    handle_signals=False,
                    close_bot_session=False,
                )
            )
            stop_wait_task = asyncio.create_task(stop_event.wait())
            done, _ = await asyncio.wait(
                {polling_task, stop_wait_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if polling_task in done:
                await polling_task
            else:
                await dispatcher.stop_polling()
                await polling_task
            stop_wait_task.cancel()
            await asyncio.gather(stop_wait_task, return_exceptions=True)
    finally:
        stop_event.set()
        await worker_task
        await runner.cleanup()
        if settings.bot_mode == "webhook":
            await dispatcher.emit_shutdown(bot=bot)
        await bot.session.close()
        await storage.close()
        await database.close()


if __name__ == "__main__":
    asyncio.run(main())
