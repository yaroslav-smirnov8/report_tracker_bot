import pytz
from app.core.db import Session
from app.core.models import Settings, ChatMember, DailyRecord
from app.core.config import DEFAULT_TIMEZONE


def get_settings(chat_id):
    session = Session()
    settings = session.query(Settings).filter_by(chat_id=chat_id).first()
    session.close()
    return settings or Settings()


def get_chat_timezone(chat_id):
    session = Session()
    settings = session.query(Settings).filter_by(chat_id=chat_id).first()
    tz_name = settings.timezone if settings and settings.timezone else DEFAULT_TIMEZONE
    session.close()
    try:
        return pytz.timezone(tz_name)
    except Exception:
        return pytz.timezone(DEFAULT_TIMEZONE)


def set_chat_timezone(chat_id, tz_name):
    session = Session()
    settings = session.query(Settings).filter_by(chat_id=chat_id).first()
    if settings:
        settings.timezone = tz_name
    else:
        settings = Settings(chat_id=chat_id, timezone=tz_name)
        session.add(settings)
    session.commit()
    session.close()


def is_admin(user_id, chat_id, bot):
    try:
        chat = bot.get_chat(chat_id)
        if chat.type == "private":
            return True
        chat_administrators = bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in chat_administrators)
    except Exception:
        return False


def update_daily_record(chat_id, user_id, date, morning_hashtag=None, evening_hashtag=None, week_hashtag=None):
    session = Session()
    member = session.query(ChatMember).filter_by(chat_id=chat_id, user_id=user_id).first()

    if member:
        record = session.query(DailyRecord).filter_by(chat_member_id=member.id, date=date).first()
        if not record:
            record = DailyRecord(chat_member_id=member.id, date=date,
                                 morning_hashtag='1' if morning_hashtag else '0',
                                 evening_hashtag='1' if evening_hashtag else '0',
                                 week_hashtag='1' if week_hashtag else '0')
            session.add(record)
        else:
            if morning_hashtag is not None:
                record.morning_hashtag = '1' if morning_hashtag else '0'
            if evening_hashtag is not None:
                record.evening_hashtag = '1' if evening_hashtag else '0'
            if week_hashtag is not None:
                record.week_hashtag = '1' if week_hashtag else '0'

        session.commit()
    session.close()


def create_user_mention(user_name, user_id, full_name):
    if user_name and user_name.strip() != "":
        return f"@{user_name}"
    return f"<a href='tg://user?id={user_id}'>{full_name}</a>"
