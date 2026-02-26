from app.core.models import Chat, ChatMember, DailyRecord
from app.services.settings_service import update_daily_record


def test_update_daily_record_creates_entry(session_factory):
    session = session_factory()
    chat = Chat(id=-1001, start_date="2026-02-01")
    member = ChatMember(chat_id=-1001, user_id=10, user_name="tester", full_name="Test User")
    session.add(chat)
    session.add(member)
    session.commit()
    session.close()

    update_daily_record(-1001, 10, "2026-02-02", morning_hashtag=True)

    session = session_factory()
    record = session.query(DailyRecord).filter_by(date="2026-02-02").first()
    assert record is not None
    assert record.morning_hashtag == "1"
    assert record.evening_hashtag == "0"
    session.close()
