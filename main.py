from telegram.ext import Updater
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.config import BOT_TOKEN
from app.core.db import init_db
from app.handlers.handlers import register_handlers
from app.services.scheduler_service import reschedule_jobs, check_and_schedule_messages


def main():
    # Fail fast if the environment is not configured for a production-safe run.
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    # Database must be ready before the bot starts scheduling or handling updates.
    init_db()

    # Telegram bot setup is intentionally minimal here to keep entry point readable.
    updater = Updater(BOT_TOKEN, use_context=True)
    bot = updater.bot
    dp = updater.dispatcher
    scheduler = BackgroundScheduler()
    scheduler.start()

    # Recreate background jobs on every start to stay in sync with current settings.
    reschedule_jobs(scheduler, bot)
    check_and_schedule_messages(scheduler, bot)
    register_handlers(dp, scheduler, bot)

    # Start polling only after all handlers and background jobs are registered.
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
