from telegram.ext import CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta, time
import pytz
from functools import partial
import re
from app.core.config import logger
from app.core.db import Session
from app.reports.excel_reports import send_excel_file_in_private, expected_report_count, completed_report_count, parse_record_date
from app.core.models import Chat, ChatMember, DailyRecord, Settings
from app.services.scheduler_service import (
    reschedule_jobs,
    check_and_schedule_messages,
    check_hashtags_and_notify,
    reschedule_chat_jobs,
    reschedule_course_completion_message
)
from app.services.settings_service import (
    get_settings,
    get_chat_timezone,
    set_chat_timezone,
    is_admin,
    update_daily_record
)


def build_help_text():
    return (
        "Bot commands:\n"
        "/menu — open the actions menu\n"
        "/buttons — open the actions menu\n"
        "/join — register as a participant\n"
        "/today — show expected hashtags for today\n"
        "/setstartdate YYYY-MM-DD — set the course start date\n"
        "/settimezone Europe/Moscow — set the chat timezone\n"
        "/remove USER_ID — remove a participant by ID\n"
        "/status — show current settings\n"
        "/help — show this help\n\n"
        "How to submit reports:\n"
        "Morning: #morning1, #morning2, ...\n"
        "Evening: #evening1, #evening2, ...\n"
        "Weekly (Sundays): #week1, #week2, ..."
    )


def build_faq_text():
    return (
        "FAQ:\n"
        "1) Reports use day numbers from the course start date.\n"
        "2) Morning and evening reports are expected on weekdays.\n"
        "3) Weekly report is expected on Sundays only.\n"
        "4) If you submitted the right hashtag, it will be counted automatically."
    )


def build_status_text(chat_id):
    # Builds a single snapshot of settings so admins can copy/paste it as a reference.
    settings = get_settings(chat_id)
    timezone = get_chat_timezone(chat_id)
    start_date = get_course_start_date(chat_id) or "Not set"
    morning_tag = settings.morning_hashtag or "#morning"
    evening_tag = settings.evening_hashtag or "#evening"
    week_tag = settings.week_hashtag or "#week"
    morning_deadline = settings.morning_deadline or "10:00"
    evening_deadline = settings.evening_deadline or "23:59"
    today_date = datetime.now(timezone).date()
    course_day_text = "Not set"
    course_week_text = "Not set"

    if start_date != "Not set":
        try:
            start_date_value = datetime.strptime(start_date, '%Y-%m-%d').date()
            day_number = (today_date - start_date_value).days + 1
            if day_number < 1:
                course_day_text = f"Starts in {abs(day_number) + 1} day(s)"
                course_week_text = "Not started"
            else:
                course_day_text = str(day_number)
                course_week_text = str((day_number - 1) // 7 + 1)
        except Exception:
            course_day_text = "Invalid start date"
            course_week_text = "Invalid start date"

    return (
        "Current settings:\n"
        f"Timezone: {timezone.zone}\n"
        f"Start date: {start_date}\n"
        f"Course day: {course_day_text}\n"
        f"Course week: {course_week_text}\n"
        f"Morning hashtag: {morning_tag}\n"
        f"Evening hashtag: {evening_tag}\n"
        f"Weekly hashtag: {week_tag}\n"
        f"Morning deadline: {morning_deadline}\n"
        f"Evening deadline: {evening_deadline}\n"
        "Weekly deadline: Sunday 23:59"
    )


def parse_time_value(value, fallback_value):
    try:
        parsed = datetime.strptime(value, "%H:%M").time()
        return parsed
    except Exception:
        return datetime.strptime(fallback_value, "%H:%M").time()


def build_today_deadlines_text(chat_id):
    # Deadlines are calculated in the chat timezone to avoid cross-region confusion.
    settings = get_settings(chat_id)
    chat_tz = get_chat_timezone(chat_id)
    now = datetime.now(chat_tz)
    today = now.date()
    is_sunday = today.weekday() == 6

    morning_time = parse_time_value(settings.morning_deadline or "10:00", "10:00")
    evening_time = parse_time_value(settings.evening_deadline or "23:59", "23:59")
    weekly_time = time(23, 59)

    lines = [f"Today's deadlines ({chat_tz.zone}):"]
    if is_sunday:
        lines.append(f"Weekly report: {weekly_time.strftime('%H:%M')}")
    else:
        lines.append(f"Morning report: {morning_time.strftime('%H:%M')}")
        lines.append(f"Evening report: {evening_time.strftime('%H:%M')}")
    return "\n".join(lines)


def build_next_deadline_text(chat_id):
    # Scan the next week to find the closest future deadline across all report types.
    settings = get_settings(chat_id)
    chat_tz = get_chat_timezone(chat_id)
    now = datetime.now(chat_tz)

    morning_time = parse_time_value(settings.morning_deadline or "10:00", "10:00")
    evening_time = parse_time_value(settings.evening_deadline or "23:59", "23:59")
    weekly_time = time(23, 59)

    candidates = []
    for day_offset in range(0, 8):
        day = (now + timedelta(days=day_offset)).date()
        weekday = day.weekday()

        if weekday == 6:
            weekly_dt = chat_tz.localize(datetime.combine(day, weekly_time))
            if weekly_dt > now:
                candidates.append(("Weekly report", weekly_dt))
        else:
            morning_dt = chat_tz.localize(datetime.combine(day, morning_time))
            evening_dt = chat_tz.localize(datetime.combine(day, evening_time))
            if morning_dt > now:
                candidates.append(("Morning report", morning_dt))
            if evening_dt > now:
                candidates.append(("Evening report", evening_dt))

    if not candidates:
        return "No upcoming deadlines found."

    next_label, next_dt = sorted(candidates, key=lambda item: item[1])[0]
    return (
        "Next deadline:\n"
        f"{next_label}: {next_dt.strftime('%Y-%m-%d %H:%M')} ({chat_tz.zone})"
    )


def build_report_templates_text(chat_id):
    chat_tz = get_chat_timezone(chat_id)
    today_date = datetime.now(chat_tz).date()
    start_date_str = get_course_start_date(chat_id)
    settings = get_settings(chat_id)
    morning_tag = settings.morning_hashtag or "#morning"
    evening_tag = settings.evening_hashtag or "#evening"
    week_tag = settings.week_hashtag or "#week"

    if not start_date_str:
        return "Start date is not set. Use /setstartdate or the menu."

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except Exception:
        return "Start date is invalid. Set it again with /setstartdate."

    day_number = (today_date - start_date).days + 1
    if day_number < 1:
        return "Start date is in the future. Templates will be available after the start date."
    if day_number > 63:
        return "The course appears to be finished. Templates are no longer generated."

    week_number = (day_number - 1) // 7 + 1
    lines = [
        "Today's templates:",
        f"Morning: {morning_tag}{day_number}",
        f"Evening: {evening_tag}{day_number}"
    ]
    if today_date.weekday() == 6:
        lines.append(f"Weekly: {week_tag}{week_number}")
    else:
        lines.append(f"Weekly (Sundays): {week_tag}{week_number}")
    return "\n".join(lines)


def build_user_progress_text(chat_id, user_id):
    session = Session()
    member = session.query(ChatMember).filter_by(chat_id=chat_id, user_id=user_id).first()
    if not member:
        session.close()
        return "You are not registered. Use /join to register."

    records = session.query(DailyRecord).filter_by(chat_member_id=member.id).all()
    today_date = datetime.now(get_chat_timezone(chat_id)).date()

    start_date_str = get_course_start_date(chat_id)
    start_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except Exception:
            start_date = None

    if not start_date:
        record_dates = [parse_record_date(record.date) for record in records]
        record_dates = [value for value in record_dates if value]
        start_date = min(record_dates) if record_dates else None

    if not start_date:
        session.close()
        return "No reports found yet."

    expected_total = expected_report_count(start_date, today_date)
    completed_total = completed_report_count(records)
    completion_rate = (completed_total / expected_total) * 100 if expected_total else 0

    last_report_date = None
    for record in records:
        record_date = parse_record_date(record.date)
        if record_date and (last_report_date is None or record_date > last_report_date):
            last_report_date = record_date

    last_report_text = last_report_date.strftime('%Y-%m-%d') if last_report_date else "No reports yet"

    session.close()
    return (
        "Your progress:\n"
        f"Completion: {completion_rate:.1f}% ({completed_total}/{expected_total})\n"
        f"Last report date: {last_report_text}"
    )


def format_log_context(chat_id, user_id=None):
    if user_id is None:
        return f"[chat_id={chat_id}]"
    return f"[chat_id={chat_id} user_id={user_id}]"


def start(update, context):
    update.message.reply_text(
        "Hi! I track report hashtags and compile analytics.\n"
        "Open the menu: /menu\n"
        "Help: /help"
    )


def help_command(update, context):
    update.message.reply_text(build_help_text())


def status_command(update, context):
    chat_id = update.message.chat_id
    update.message.reply_text(build_status_text(chat_id))


def today_command(update, context):
    chat_id = update.message.chat_id
    update.message.reply_text(build_report_templates_text(chat_id))


def show_buttons(update, context):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    bot = context.bot
    admin = is_admin(user_id, chat_id, bot)

    # Participant menu is always visible; admin menu is appended conditionally.
    participant_buttons = [
        [InlineKeyboardButton("Report templates", callback_data='report_templates')],
        [InlineKeyboardButton("Today's hashtags", callback_data='today_hashtags')],
        [InlineKeyboardButton("My progress", callback_data='my_progress')],
        [InlineKeyboardButton("Status", callback_data='show_status')],
        [InlineKeyboardButton("Today's deadlines", callback_data='deadlines_today')],
        [InlineKeyboardButton("Next deadline", callback_data='next_deadline')],
        [InlineKeyboardButton("FAQ", callback_data='show_faq')],
        [InlineKeyboardButton("Help", callback_data='show_help')],
    ]

    admin_buttons = [
        [InlineKeyboardButton("Send report to DM", callback_data='send_report_in_private')],
        [InlineKeyboardButton("Set start date", callback_data='set_start_date')],
        [InlineKeyboardButton("Set timezone", callback_data='set_timezone')],
        [InlineKeyboardButton("Remove participant", callback_data='show_participants')],
    ]

    keyboard = participant_buttons + admin_buttons if admin else participant_buttons
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Choose an action:', reply_markup=reply_markup)


def button(update, context):
    query = update.callback_query
    query.answer()
    chat_id = query.message.chat_id
    user_id = query.from_user.id

    callback_data = query.data
    bot = context.bot

    admin_only_actions = {
        'send_report_in_private',
        'show_participants',
        'set_start_date',
        'set_timezone'
    }
    is_admin_action = callback_data in admin_only_actions or callback_data.startswith('remove_')

    # Guard admin-only flows even if a user crafts callback data manually.
    if is_admin_action and not is_admin(user_id, chat_id, bot):
        query.edit_message_text(text="Available to administrators only. Help: /help")
        return

    if callback_data.startswith('remove_'):
        user_id_to_remove = int(callback_data.split('_')[1])
        remove_member_from_chat(chat_id, user_id_to_remove)
        query.edit_message_text(text=f"Participant with ID {user_id_to_remove} was removed.")
    elif callback_data == 'show_participants':
        show_participants(update, context)
    elif callback_data == 'send_report_in_private':
        try:
            was_sent = send_excel_file_in_private(update, context)
            if was_sent:
                query.edit_message_text(text="The report was sent to your DM.")
            else:
                query.edit_message_text(text="Open this in the target group to send the report.")
        except Exception:
            logger.exception(f"Failed to send report {format_log_context(chat_id, user_id)}")
            query.edit_message_text(text="Failed to send the report.")
        return
    elif callback_data == 'report_templates':
        query.edit_message_text(text=build_report_templates_text(chat_id))
        return
    elif callback_data == 'today_hashtags':
        query.edit_message_text(text=build_report_templates_text(chat_id))
        return
    elif callback_data == 'show_status':
        query.edit_message_text(text=build_status_text(chat_id))
        return
    elif callback_data == 'deadlines_today':
        query.edit_message_text(text=build_today_deadlines_text(chat_id))
        return
    elif callback_data == 'next_deadline':
        query.edit_message_text(text=build_next_deadline_text(chat_id))
        return
    elif callback_data == 'my_progress':
        progress_text = build_user_progress_text(chat_id, user_id)
        try:
            context.bot.send_message(chat_id=user_id, text=progress_text)
            query.edit_message_text(text="Your progress was sent to your DM.")
        except Exception:
            logger.exception(f"Failed to send progress {format_log_context(chat_id, user_id)}")
            query.edit_message_text(text="Failed to send your progress to DM.")
        return
    elif callback_data == 'show_faq':
        query.edit_message_text(text=build_faq_text())
        return
    elif callback_data == 'set_start_date':
        query.edit_message_text(text="Send the start date in YYYY-MM-DD format.")
        return
    elif callback_data == 'set_timezone':
        query.edit_message_text(text="Send the timezone name, e.g. Europe/Moscow.")
        return
    elif callback_data == 'show_help':
        query.edit_message_text(text=build_help_text())
        return

    logger.info(f"Button clicked {format_log_context(chat_id, user_id)}: {callback_data}")


def join(update, context):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    user_name = update.message.from_user.username
    first_name = update.message.from_user.first_name
    last_name = update.message.from_user.last_name

    try:
        response = add_member_to_chat(chat_id, user_id, user_name, first_name, last_name)
        update.message.reply_text(response)
    except Exception:
        logger.exception(f"Failed to add participant {format_log_context(chat_id, user_id)}")
        update.message.reply_text('Failed to add participant. Please try again later.')


def add_member_to_chat(chat_id, user_id, user_name, first_name, last_name):
    session = Session()
    full_name = f"{first_name or ''} {last_name or ''}".strip()
    chat = session.query(Chat).filter_by(id=chat_id).first()
    if not chat:
        chat = Chat(id=chat_id, start_date=None)
        session.add(chat)
        session.commit()
    member = session.query(ChatMember).filter_by(chat_id=chat_id, user_id=user_id).first()

    if not member:
        logger.info(f"Adding new member {format_log_context(chat_id, user_id)}")
        member = ChatMember(chat_id=chat_id, user_id=user_id, user_name=user_name, full_name=full_name)
        session.add(member)
        session.commit()
        session.close()
        logger.info("New member added successfully.")
        return 'You have been added to the participant list.'
    else:
        logger.info(f"Member already exists {format_log_context(chat_id, user_id)}")
        if member.user_name != user_name or member.full_name != full_name:
            logger.info(f"Updating member info {format_log_context(chat_id, user_id)}")
            member.user_name = user_name
            member.full_name = full_name
            session.commit()
            logger.info("Member info updated successfully.")
        session.close()
        return 'You are already registered.'


def button_callback_handler(update, context):
    query = update.callback_query
    query.answer()

    user_id_to_add = query.data
    query.edit_message_text(text=f"Participant with ID {user_id_to_add} added.")


def add_member(user_id, chat_id):
    session = Session()
    chat = session.query(Chat).filter_by(id=chat_id).first()
    if not chat:
        chat = Chat(id=chat_id, start_date=None)
        session.add(chat)
        session.commit()
    existing_member = session.query(ChatMember).filter_by(user_id=user_id, chat_id=chat_id).first()
    if not existing_member:
        new_member = ChatMember(user_id=user_id, chat_id=chat_id)
        session.add(new_member)
        session.commit()
        session.close()
        return f"Participant with ID {user_id} added."
    else:
        session.close()
        return f"Participant with ID {user_id} already exists."


def create_member_buttons(bot, chat_id):
    chat_members = bot.get_chat_administrators(chat_id)
    keyboard = []

    for member in chat_members:
        if member.user.id != bot.id:
            button_text = f"{member.user.first_name} {member.user.last_name or ''}"
            callback_data = f"add_{member.user.id}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    return InlineKeyboardMarkup(keyboard)


def is_valid_week_report(date_str):
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    return date_obj.weekday() == 6


def cancel(update, context):
    update.message.reply_text('Operation cancelled.')
    return ConversationHandler.END


def remove_member_from_chat(chat_id, user_id):
    session = Session()
    member = session.query(ChatMember).filter_by(chat_id=chat_id, user_id=user_id).first()
    if member:
        session.delete(member)
        session.commit()
    session.close()


def get_course_start_date(chat_id):
    session = Session()
    chat = session.query(Chat).filter_by(id=chat_id).first()
    if chat and chat.start_date:
        start_date = chat.start_date
        session.close()
        return start_date
    settings = session.query(Settings).filter_by(chat_id=chat_id).first()
    if settings and settings.start_date:
        start_date = settings.start_date
        session.close()
        return start_date
    session.close()
    return None


def set_course_start_date(chat_id, start_date):
    session = Session()
    chat = session.query(Chat).filter_by(id=chat_id).first()
    if not chat:
        chat = Chat(id=chat_id, start_date=start_date)
        session.add(chat)
    else:
        chat.start_date = start_date
    settings = session.query(Settings).filter_by(chat_id=chat_id).first()
    if settings:
        settings.start_date = start_date
    else:
        settings = Settings(chat_id=chat_id, start_date=start_date)
        session.add(settings)
    session.commit()
    session.close()


def set_start_date(update, context):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    bot = context.bot
    scheduler = context.bot_data.get("scheduler")

    if not is_admin(user_id, chat_id, bot):
        update.message.reply_text("Only administrators can change the course start date.")
        return ConversationHandler.END

    try:
        start_date_str = context.args[0]
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        set_course_start_date(chat_id, start_date)
        if scheduler:
            reschedule_course_completion_message(scheduler, bot, chat_id, start_date_str)
        update.message.reply_text(f'Course start date set to {start_date}.')
    except (IndexError, ValueError):
        update.message.reply_text('Invalid date format. Example: /setstartdate 2024-01-31')

    return ConversationHandler.END


def set_start_date_from_text(update, context):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    bot = context.bot
    scheduler = context.bot_data.get("scheduler")

    if not is_admin(user_id, chat_id, bot):
        update.message.reply_text("Only administrators can change the course start date.")
        return ConversationHandler.END

    start_date_str = update.message.text.strip()
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        set_course_start_date(chat_id, start_date)
        if scheduler:
            reschedule_course_completion_message(scheduler, bot, chat_id, start_date_str)
        update.message.reply_text(f'Course start date set to {start_date}.')
        return ConversationHandler.END
    except Exception:
        update.message.reply_text('Invalid date format. Example: 2024-01-31')
        return 'SET_START_DATE'


def set_timezone(update, context):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    bot = context.bot
    scheduler = context.bot_data.get("scheduler")

    if not is_admin(user_id, chat_id, bot):
        update.message.reply_text("Only administrators can change the timezone.")
        return

    if not context.args:
        update.message.reply_text("Provide a timezone name. Example: /settimezone Europe/Moscow")
        return

    tz_name = context.args[0]
    try:
        pytz.timezone(tz_name)
    except Exception:
        update.message.reply_text("Invalid timezone name. Example: Europe/Moscow")
        return

    set_chat_timezone(chat_id, tz_name)
    if scheduler:
        reschedule_chat_jobs(scheduler, bot, chat_id)
        start_date_str = get_course_start_date(chat_id)
        if start_date_str:
            reschedule_course_completion_message(scheduler, bot, chat_id, start_date_str)
    update.message.reply_text(f"Timezone set to {tz_name}.")


def set_timezone_from_text(update, context):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    bot = context.bot
    scheduler = context.bot_data.get("scheduler")

    if not is_admin(user_id, chat_id, bot):
        update.message.reply_text("Only administrators can change the timezone.")
        return ConversationHandler.END

    tz_name = update.message.text.strip()
    try:
        pytz.timezone(tz_name)
    except Exception:
        update.message.reply_text("Invalid timezone name. Example: Europe/Moscow")
        return 'SET_TIMEZONE'

    set_chat_timezone(chat_id, tz_name)
    if scheduler:
        reschedule_chat_jobs(scheduler, bot, chat_id)
        start_date_str = get_course_start_date(chat_id)
        if start_date_str:
            reschedule_course_completion_message(scheduler, bot, chat_id, start_date_str)
    update.message.reply_text(f"Timezone set to {tz_name}.")
    return ConversationHandler.END


def start_set_start_date(update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    bot = context.bot
    query.answer()

    if not is_admin(user_id, chat_id, bot):
        query.edit_message_text(text="Only administrators can change the course start date.")
        return ConversationHandler.END

    query.edit_message_text(text="Send the start date in YYYY-MM-DD format.")
    return 'SET_START_DATE'


def start_set_timezone(update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    bot = context.bot
    query.answer()

    if not is_admin(user_id, chat_id, bot):
        query.edit_message_text(text="Only administrators can change the timezone.")
        return ConversationHandler.END

    query.edit_message_text(text="Send the timezone name, e.g. Europe/Moscow.")
    return 'SET_TIMEZONE'


def show_participants(update, context):
    query = update.callback_query
    query.answer()
    chat_id = query.message.chat_id
    session = Session()
    members = session.query(ChatMember).filter_by(chat_id=chat_id).all()
    keyboard = []

    for member in members:
        button_text = f"{member.user_name or member.user_id}"
        callback_data = f"remove_{member.user_id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text='Select a participant to remove:', reply_markup=reply_markup)
    session.close()


def get_all_chats():
    session = Session()
    chats = session.query(Settings).all()
    session.close()
    return chats


def remove_member(update, context):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    bot = context.bot

    if not is_admin(user_id, chat_id, bot):
        update.message.reply_text('Only administrators can remove participants.')
        return

    try:
        user_id_to_remove = int(context.args[0])
        remove_member_from_chat(chat_id, user_id_to_remove)
        update.message.reply_text(f'Participant with ID {user_id_to_remove} was removed.')
    except (IndexError, ValueError):
        update.message.reply_text('Invalid command format. Example: /remove 123456')


def handle_new_member(update, context, scheduler, bot):
    for member in update.message.new_chat_members:
        add_member_to_chat(update.message.chat_id, member.id, member.username, member.first_name, member.last_name)
        reschedule_jobs(scheduler, bot)
        check_and_schedule_messages(scheduler, bot)
        check_hashtags_and_notify(bot)


def handle_left_member(update, context):
    remove_member_from_chat(update.message.chat_id, update.message.left_chat_member.id)


def handle_message(update, context):
    if update.edited_message:
        chat_id = update.edited_message.chat.id
        user_id = update.edited_message.from_user.id
        user_name = update.edited_message.from_user.username
        first_name = update.edited_message.from_user.first_name
        last_name = update.edited_message.from_user.last_name or ""
        new_user_name = update.edited_message.from_user.username
    else:
        chat_id = update.message.chat_id
        user_id = update.message.from_user.id
        user_name = update.message.from_user.username
        first_name = update.message.from_user.first_name
        last_name = update.message.from_user.last_name or ""
        new_user_name = update.message.from_user.username

    if user_id == context.bot.id:
        logger.info(f"Bot message skipped {format_log_context(chat_id, user_id)}")
        return

    session = Session()
    member = session.query(ChatMember).filter_by(chat_id=chat_id, user_id=user_id).first()
    if member:
        if member.user_name != new_user_name:
            member.user_name = new_user_name
            session.commit()
    session.close()

    message = update.message if update.message else update.edited_message

    text_to_process = None
    if message:
        if message.text:
            text_to_process = message.text.lower()
        elif message.caption:
            text_to_process = message.caption.lower()

    logger.info(f"Received a message {format_log_context(chat_id, user_id)}")
    logger.info(f"Text to process {format_log_context(chat_id, user_id)}: '{text_to_process}'")

    chat_tz = get_chat_timezone(chat_id)
    current_time = datetime.now(chat_tz)
    today_date = current_time.date()
    start_date_str = get_course_start_date(chat_id)

    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        current_time = datetime.now(chat_tz)
        today_date = current_time.date()

        day_number = (today_date - start_date).days + 1
        week_number = (day_number - 1) // 7 + 1

        if 1 <= day_number <= 63:
            settings = get_settings(chat_id)
            morning_tag = settings.morning_hashtag if settings.morning_hashtag else "#morning"
            evening_tag = settings.evening_hashtag if settings.evening_hashtag else "#evening"
            week_tag = settings.week_hashtag if settings.week_hashtag else "#week"
            possible_hashtags = [
                f"{morning_tag}{day_number}",
                f"{evening_tag}{day_number}",
                f"{week_tag}{week_number}",
            ]

            if text_to_process:
                logger.info(f"Received a message {format_log_context(chat_id, user_id)}")
                logger.info(f"Text to process {format_log_context(chat_id, user_id)}: '{text_to_process}'")

            else:
                logger.info(f"No text or caption {format_log_context(chat_id, user_id)}")

            if any(hashtag in text_to_process for hashtag in possible_hashtags):
                logger.info(f"Hashtag found {format_log_context(chat_id, user_id)}: {text_to_process}")

                add_member_to_chat(chat_id, user_id, user_name, first_name, last_name)

                morning_deadline = time(10, 1)
                evening_deadline = time(23, 59)

                if f"{morning_tag}{day_number}" in text_to_process and current_time.time() < morning_deadline:
                    update_daily_record(chat_id, user_id, today_date.strftime('%Y-%m-%d'), morning_hashtag=True)
                elif f"{evening_tag}{day_number}" in text_to_process and current_time.time() < evening_deadline:
                    update_daily_record(chat_id, user_id, today_date.strftime('%Y-%m-%d'), evening_hashtag=True)
                elif f"{week_tag}{week_number}" in text_to_process and current_time.weekday() == 6:
                    update_daily_record(chat_id, user_id, today_date.strftime('%Y-%m-%d'), week_hashtag=True)

                if today_date != datetime.now(chat_tz).date():
                    logger.info(f"Message from previous day {format_log_context(chat_id, user_id)}")
                    return

                else:
                    logger.info(f"No fine hashtag found {format_log_context(chat_id, user_id)}")
                return
            else:
                if text_to_process:
                    tag_pattern = rf"({re.escape(morning_tag)}|{re.escape(evening_tag)}|{re.escape(week_tag)})(\d+)"
                    match = re.search(tag_pattern, text_to_process)
                    if match:
                        base_tag = match.group(1)
                        provided_number = int(match.group(2))
                        expected_number = week_number if base_tag == week_tag else day_number
                        if provided_number != expected_number:
                            update.message.reply_text(
                                f"Expected hashtag for today: {base_tag}{expected_number}"
                            )
                logger.info(f"No relevant hashtag found {format_log_context(chat_id, user_id)}")
        else:
            logger.info(f"Message date outside range {format_log_context(chat_id, user_id)}")
    else:
        if text_to_process:
            if re.search(r"(#morning|#evening|#week)\d+", text_to_process):
                update.message.reply_text("Course start date is not set. Use /setstartdate YYYY-MM-DD.")
        logger.info(f"Start date not set {format_log_context(chat_id, user_id)}")


def error(update, context):
    logger.error('Update error', exc_info=context.error)


def register_handlers(dp, scheduler, bot):
    # Keep handler registration centralized to make bot behavior discoverable.
    custom_handle_new_member = partial(handle_new_member, scheduler=scheduler, bot=bot)
    dp.bot_data["scheduler"] = scheduler
    settings_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_set_start_date, pattern='^set_start_date$'),
            CallbackQueryHandler(start_set_timezone, pattern='^set_timezone$')
        ],
        states={
            'SET_START_DATE': [MessageHandler(Filters.text & ~Filters.command, set_start_date_from_text)],
            'SET_TIMEZONE': [MessageHandler(Filters.text & ~Filters.command, set_timezone_from_text)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dp.add_handler(settings_conv_handler)
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("menu", show_buttons))
    dp.add_handler(CommandHandler("buttons", show_buttons))
    dp.add_handler(CommandHandler("today", today_command))
    dp.add_handler(CommandHandler("status", status_command))
    dp.add_handler(CommandHandler("setstartdate", set_start_date, pass_args=True))
    dp.add_handler(CommandHandler("settimezone", set_timezone, pass_args=True))
    dp.add_handler(CommandHandler("remove", remove_member, pass_args=True))
    dp.add_handler(CommandHandler('join', join))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(
        MessageHandler(Filters.update.message & (Filters.text | Filters.caption) & ~Filters.command, handle_message))
    dp.add_handler(MessageHandler(Filters.update.edited_message, handle_message))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, custom_handle_new_member))
    dp.add_handler(MessageHandler(Filters.status_update.left_chat_member, handle_left_member))
    dp.add_error_handler(error)
