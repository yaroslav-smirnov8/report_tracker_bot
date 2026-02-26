from datetime import datetime, timedelta, time
import pytz
import random
from app.core.config import DEFAULT_TIMEZONE, logger
from app.core.db import Session
from app.core.models import Chat, ChatMember, DailyRecord
from app.services.settings_service import get_chat_timezone, create_user_mention


def format_log_context(chat_id, user_id=None):
    if user_id is None:
        return f"[chat_id={chat_id}]"
    return f"[chat_id={chat_id} user_id={user_id}]"


def check_reports_and_notify(bot):
    # Daily audit of missing reports with tailored reminders per chat.
    logger.info("check_reports_and_notify: start")
    session = Session()
    logger.info("Function check_reports_and_notify started")

    chats = session.query(Chat).all()
    for chat in chats:
        logger.info("check_reports_and_notify: chat processing")
        chat_id = chat.id
        chat_tz = get_chat_timezone(chat_id)
        current_time = datetime.now(chat_tz)
        today_date = current_time.date()
        is_weekday_sunday = current_time.weekday() == 6
        is_morning = current_time.time() < time(12, 0, 0)
        late_users_morning = []
        late_users_evening = []
        late_users_week = []

        logger.info(f"Processing chat {format_log_context(chat_id)}")
        try:
            logger.info(f"Chat processing started {format_log_context(chat_id)}")
            members = session.query(ChatMember).filter_by(chat_id=chat_id).all()
            member_ids = [member.id for member in members]
            date_str = today_date.strftime('%Y-%m-%d')
            records_by_member = {}
            if member_ids:
                records = session.query(DailyRecord).filter(
                    DailyRecord.chat_member_id.in_(member_ids),
                    DailyRecord.date == date_str
                ).all()
                records_by_member = {record.chat_member_id: record for record in records}
            for member in members:
                logger.info(f"check_reports_and_notify {format_log_context(chat_id, member.user_id)}")
                record = records_by_member.get(member.id)

                if is_morning and not is_weekday_sunday:
                    if not record or record.morning_hashtag != "1":
                        user_mention = create_user_mention(member.user_name, member.user_id, member.full_name)
                        late_users_morning.append(user_mention)

                if not is_morning and not is_weekday_sunday:
                    if not record or record.evening_hashtag != "1":
                        user_mention = create_user_mention(member.user_name, member.user_id, member.full_name)
                        late_users_evening.append(user_mention)

                if is_weekday_sunday and (not record or record.week_hashtag != "1"):
                    user_mention = create_user_mention(member.user_name, member.user_id, member.full_name)
                    late_users_week.append(user_mention)

            praise_messages = [
                "Outstanding work! Your reports are on point. 🌟",
                "Great job! Consistency is your superpower. 💪",
                "Excellent effort! Keep the momentum going. 🚀",
                "Well done! Your discipline is inspiring. 👏",
                "Strong performance today. Keep it up! ✅",
                "Fantastic commitment! You set the bar high. 🏅"
            ]
            random_praise = random.choice(praise_messages)

            if not is_weekday_sunday:
                if is_morning and late_users_morning:
                    send_notification(bot, chat_id, late_users_morning, "morning report")
                    logger.info(f"check_reports_and_notify: notify missing morning reports {format_log_context(chat_id)}")
                else:
                    logger.info(f"No late users for morning report {format_log_context(chat_id)}")
                if late_users_evening and not is_morning:
                    send_notification(bot, chat_id, late_users_evening, "evening report")
                    logger.info(f"check_reports_and_notify: notify missing evening reports {format_log_context(chat_id)}")
                else:
                    logger.info(f"No late users for evening report {format_log_context(chat_id)}")

            if is_weekday_sunday and late_users_week:
                send_notification(bot, chat_id, late_users_week, "weekly report")
                logger.info(f"check_reports_and_notify: notify missing weekly reports {format_log_context(chat_id)}")
            else:
                logger.info(f"No late users for weekly report {format_log_context(chat_id)}")

            if not is_weekday_sunday:
                if is_morning and not late_users_morning:
                    bot.send_message(chat_id=chat_id,
                                     text="All participants submitted morning reports on time. Great job! " + random_praise)
                    logger.info(f"All morning reports submitted on time {format_log_context(chat_id)}")
                if not is_morning and not late_users_evening:
                    bot.send_message(chat_id=chat_id,
                                     text="All participants submitted evening reports on time. Great job! " + random_praise)
                    logger.info(f"All evening reports submitted on time {format_log_context(chat_id)}")
            if is_weekday_sunday:
                if not late_users_week:
                    bot.send_message(chat_id=chat_id,
                                     text="All participants submitted weekly reports on time. Excellent work! " + random_praise)
                    logger.info(f"All weekly reports submitted on time {format_log_context(chat_id)}")
            logger.info(f"Chat processing finished {format_log_context(chat_id)}")
        except Exception as e:
            logger.error(f"Chat error {format_log_context(chat_id)}: {str(e)}")

    session.close()
    logger.info("Function check_reports_and_notify completed")


def send_notification(bot, chat_id, user_list, report_type):
    session = Session()
    chat = session.query(Chat).filter(Chat.id == chat_id).first()
    if chat and user_list:
        current_date = datetime.now().date()
        start_date = datetime.strptime(chat.start_date, "%Y-%m-%d").date()
        days_since_start = (current_date - start_date).days

        if days_since_start >= 5:
            late_message_variants = [
                "Looks like you missed the report today. Please catch up soon. 💙",
                "Busy day happens. Send the report when you can. 🌟",
                "Quick reminder: your report keeps the team moving forward. 🚀",
                "Small updates matter. Please submit your report today. ✅",
                "Please take a moment to submit your report. Thank you! 🙌",
                "Your report is important. Please send it as soon as possible. ⏰"
            ]
            additional_text = random.choice(late_message_variants)
        else:
            additional_text = "Please submit it as soon as possible. 😊"
        message_text = f"Late {report_type} submissions: " + ", ".join(user_list) + ". " + additional_text
        bot.send_message(chat_id=chat_id, text=message_text, parse_mode="HTML")

    session.close()


def send_final_reminder(bot, report_type):
    session = Session()
    current_time = datetime.now(pytz.timezone(DEFAULT_TIMEZONE))
    today_date = current_time.date()

    date_str = today_date.strftime('%Y-%m-%d')

    if report_type == "morning":
        condition = (DailyRecord.morning_hashtag == '0') | (DailyRecord.morning_hashtag == None)
    elif report_type == "evening":
        condition = (DailyRecord.evening_hashtag == '0') | (DailyRecord.evening_hashtag == None)
    elif report_type == "weekly" and current_time.weekday() == 6:
        condition = (DailyRecord.week_hashtag == '0') | (DailyRecord.week_hashtag == None)
    else:
        return

    records = session.query(ChatMember, DailyRecord).join(DailyRecord,
                                                          ChatMember.id == DailyRecord.chat_member_id).filter(
        DailyRecord.date == date_str, condition).all()

    late_users_by_chat = {}

    for member, record in records:
        late_users_by_chat.setdefault(member.chat_id, []).append(
            create_user_mention(member.user_name, member.user_id, member.full_name))

    for chat_id, users in late_users_by_chat.items():
        if users:
            bot.send_message(chat_id=chat_id,
                             text=f"Reminder: 15 minutes left to submit the {report_type} report. Missing: " + ", ".join(
                                 users))

    session.close()


def check_hashtags_and_notify(bot):
    session = Session()
    logger.info("check_hashtags_and_notify: start")
    # This job updates daily records and collects late reporters at the deadline.
    morning_end_time = time(10, 0, 0)
    evening_end_time = time(23, 59, 59)

    chats_to_notify = session.query(Chat).all()
    for chat in chats_to_notify:
        logger.info(f"Checking chat {format_log_context(chat.id)}")
        chat_tz = get_chat_timezone(chat.id)
        current_time = datetime.now(chat_tz)
        today_date = current_time.date()
        date_str = today_date.strftime('%Y-%m-%d')
        morning_late_users = []
        evening_late_users = []
        week_late_users = []
        is_weekday_sunday = current_time.weekday() == 6

        members = session.query(ChatMember).filter_by(chat_id=chat.id).all()
        member_ids = [member.id for member in members]
        records_by_member = {}
        if member_ids:
            records = session.query(DailyRecord).filter(
                DailyRecord.chat_member_id.in_(member_ids),
                DailyRecord.date == date_str
            ).all()
            records_by_member = {record.chat_member_id: record for record in records}

        for member in members:
            logger.info(f"check_hashtags_and_notify {format_log_context(chat.id, member.user_id)}")
            record = records_by_member.get(member.id)

            if not record:
                record = DailyRecord(chat_member_id=member.id, date=date_str,
                                     morning_hashtag="0", evening_hashtag="0", week_hashtag="0")
                session.add(record)
                records_by_member[member.id] = record

            user_mention = create_user_mention(member.user_name, member.user_id, member.full_name)

            if current_time.time() >= morning_end_time and record.morning_hashtag != "1":
                morning_late_users.append(user_mention)
                record.morning_hashtag = "0"

            if current_time.time() >= evening_end_time and record.evening_hashtag != "1":
                evening_late_users.append(user_mention)
                record.evening_hashtag = "0"

            if is_weekday_sunday and record.week_hashtag != "1":
                week_late_users.append(user_mention)
                record.week_hashtag = "0"

        session.commit()
    session.close()
    logger.info("check_hashtags_and_notify: end")


def send_hour_reminder(bot, chat_id, report_type):
    bot.send_message(chat_id=chat_id,
                     text=f"Reminder: 1 hour left to submit the {report_type} report. Please make sure to send it.")


def send_fifteen_minute_reminder(bot, chat_id, report_type):
    try:
        session = Session()
        chat_tz = get_chat_timezone(chat_id)
        current_time = datetime.now(chat_tz)
        today_date = current_time.date()
        date_str = today_date.strftime('%Y-%m-%d')
        late_users = []
        members = session.query(ChatMember).filter_by(chat_id=chat_id).all()
        member_ids = [member.id for member in members]
        records_by_member = {}
        if member_ids:
            records = session.query(DailyRecord).filter(
                DailyRecord.chat_member_id.in_(member_ids),
                DailyRecord.date == date_str
            ).all()
            records_by_member = {record.chat_member_id: record for record in records}

        for member in members:
            record = records_by_member.get(member.id)
            if not record or (report_type == "morning" and record.morning_hashtag != "1") or (
                    report_type == "evening" and record.evening_hashtag != "1"):
                user_mention = create_user_mention(member.user_name, member.user_id, member.full_name)
                late_users.append(user_mention)

        if late_users:
            message_text = f"Reminder: 15 minutes left to submit the {report_type} report. Missing: " + ", ".join(
                late_users)
            bot.send_message(chat_id=chat_id, text=message_text, parse_mode="HTML")
        else:
            logger.info(f"No late users for {report_type} report in chat {chat_id}")

        session.close()
    except Exception as e:
        session.close()
        logger.error(f"Error in send_fifteen_minute_reminder: {e}")


def get_chat_job_ids(chat_id):
    return [
        f"morning_hour_reminder_{chat_id}",
        f"morning_15min_reminder_{chat_id}",
        f"evening_hour_reminder_{chat_id}",
        f"evening_15min_reminder_{chat_id}",
        f"week_15min_reminder_{chat_id}",
        f"reports_notify_morning_{chat_id}",
        f"reports_notify_evening_{chat_id}",
        f"reports_notify_week_{chat_id}",
        f"hashtags_notify_morning_{chat_id}",
        f"hashtags_notify_evening_{chat_id}",
        f"hashtags_notify_week_{chat_id}",
        f"course_completion_{chat_id}",
    ]


def clear_chat_jobs(scheduler, chat_id):
    for job_id in get_chat_job_ids(chat_id):
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)


def schedule_chat_jobs(scheduler, bot, chat_id):
    # All per-chat scheduled jobs are defined in one place to simplify rescheduling.
    chat_tz = get_chat_timezone(chat_id)

    morning_time = time(10, 0)
    evening_time = time(23, 59)
    week_reminder_time = time(23, 59)

    morning_hour_reminder_id = f"morning_hour_reminder_{chat_id}"
    morning_fifteen_minute_reminder_id = f"morning_15min_reminder_{chat_id}"
    evening_hour_reminder_id = f"evening_hour_reminder_{chat_id}"
    evening_fifteen_minute_reminder_id = f"evening_15min_reminder_{chat_id}"
    week_fifteen_minute_reminder_id = f"week_15min_reminder_{chat_id}"
    reports_notify_morning_id = f"reports_notify_morning_{chat_id}"
    reports_notify_evening_id = f"reports_notify_evening_{chat_id}"
    reports_notify_week_id = f"reports_notify_week_{chat_id}"
    morning_job_id = f"hashtags_notify_morning_{chat_id}"
    evening_job_id = f"hashtags_notify_evening_{chat_id}"
    week_job_id = f"hashtags_notify_week_{chat_id}"

    morning_hour_reminder = (datetime.combine(datetime.today(), morning_time) - timedelta(hours=1)).time()
    morning_fifteen_minute_reminder = (
        datetime.combine(datetime.today(), morning_time) - timedelta(minutes=15)).time()
    evening_hour_reminder = (datetime.combine(datetime.today(), evening_time) - timedelta(hours=1)).time()
    evening_fifteen_minute_reminder = (
        datetime.combine(datetime.today(), evening_time) - timedelta(minutes=15)).time()
    week_fifteen_minute_reminder = (
        datetime.combine(datetime.today(), week_reminder_time) - timedelta(minutes=15)).time()

    scheduler.add_job(send_hour_reminder, 'cron', id=morning_hour_reminder_id, hour=morning_hour_reminder.hour,
                      minute=morning_hour_reminder.minute, args=(bot, chat_id, "morning"),
                      day_of_week='mon,tue,wed,thu,fri,sat', timezone=chat_tz)
    scheduler.add_job(send_fifteen_minute_reminder, 'cron', id=morning_fifteen_minute_reminder_id,
                      hour=morning_fifteen_minute_reminder.hour,
                      minute=morning_fifteen_minute_reminder.minute, args=(bot, chat_id, "morning"),
                      day_of_week='mon,tue,wed,thu,fri,sat', timezone=chat_tz)
    scheduler.add_job(send_hour_reminder, 'cron', id=evening_hour_reminder_id, hour=evening_hour_reminder.hour,
                      minute=evening_hour_reminder.minute, args=(bot, chat_id, "evening"),
                      day_of_week='mon,tue,wed,thu,fri,sat', timezone=chat_tz)
    scheduler.add_job(send_fifteen_minute_reminder, 'cron', id=evening_fifteen_minute_reminder_id,
                      hour=evening_fifteen_minute_reminder.hour,
                      minute=evening_fifteen_minute_reminder.minute, args=(bot, chat_id, "evening"),
                      day_of_week='mon,tue,wed,thu,fri,sat', timezone=chat_tz)
    scheduler.add_job(send_fifteen_minute_reminder, 'cron', id=week_fifteen_minute_reminder_id, day_of_week='sun',
                      hour=week_fifteen_minute_reminder.hour, minute=week_fifteen_minute_reminder.minute,
                      args=(bot, chat_id, "weekly"), timezone=chat_tz)

    scheduler.add_job(check_hashtags_and_notify, 'cron', id=morning_job_id,
                      day_of_week='mon,tue,wed,thu,fri,sat', hour=10, minute=1, args=[bot],
                      timezone=chat_tz)
    scheduler.add_job(check_hashtags_and_notify, 'cron', id=evening_job_id,
                      day_of_week='mon,tue,wed,thu,fri,sat', hour=23, minute=59, second=59, args=[bot],
                      timezone=chat_tz)
    scheduler.add_job(check_hashtags_and_notify, 'cron', id=week_job_id, day_of_week='sun', hour=23, minute=59,
                      args=[bot], timezone=chat_tz)

    scheduler.add_job(check_reports_and_notify, 'cron', id=reports_notify_morning_id,
                      day_of_week='mon,tue,wed,thu,fri,sat', hour=10, minute=1, args=[bot],
                      timezone=chat_tz)
    scheduler.add_job(lambda: check_reports_and_notify(bot), 'cron', id=reports_notify_evening_id,
                      day_of_week='mon,tue,wed,thu,fri,sat', hour=23, minute=59, second=59,
                      timezone=chat_tz)
    scheduler.add_job(lambda: check_reports_and_notify(bot), 'cron', id=reports_notify_week_id,
                      day_of_week='sun', hour=23, minute=59, second=59, timezone=chat_tz)


def reschedule_chat_jobs(scheduler, bot, chat_id):
    clear_chat_jobs(scheduler, chat_id)
    schedule_chat_jobs(scheduler, bot, chat_id)


def reschedule_jobs(scheduler, bot):
    # Called at startup to ensure job definitions match the stored chat settings.
    try:
        session = Session()
        chat_list = session.query(Chat).all()
        for chat in chat_list:
            reschedule_chat_jobs(scheduler, bot, chat.id)

        session.close()
        logger.info("reschedule_jobs: jobs added")
    except Exception as e:
        session.close()
        logger.error(f"reschedule_jobs: job scheduling error: {e}")


def send_course_completion_message(bot, chat_id):
    message = (
        "Congratulations to everyone who completed the course! 🌟 Your consistency and progress are impressive. "
        "Keep building on this momentum, and carry these habits into your next goals."
    )
    bot.send_message(chat_id=chat_id, text=message)


def schedule_course_completion_message(scheduler, bot, chat_id, start_date_str):
    # Completion message is scheduled once per chat at a fixed offset from start date.
    chat_tz = get_chat_timezone(chat_id)
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')

    completion_date = start_date + timedelta(days=62)

    send_time = chat_tz.localize(datetime.combine(completion_date, time(18, 0)))

    job_id = f"course_completion_{chat_id}"
    scheduler.add_job(send_course_completion_message, 'date', id=job_id, run_date=send_time, args=(bot, chat_id),
                      timezone=chat_tz)


def reschedule_course_completion_message(scheduler, bot, chat_id, start_date_str):
    job_id = f"course_completion_{chat_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    schedule_course_completion_message(scheduler, bot, chat_id, start_date_str)


def check_and_schedule_messages(scheduler, bot):
    session = Session()
    chats = session.query(Chat).all()
    for chat in chats:
        if chat.start_date:
            reschedule_course_completion_message(scheduler, bot, chat.id, chat.start_date)
    session.close()


def test_job():
    print("Test job executed", datetime.now())
