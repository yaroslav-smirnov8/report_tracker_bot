from datetime import date
from app.reports.excel_reports import (
    expected_report_count,
    completed_report_count,
    build_date_range,
    day_completion,
    calculate_member_metrics,
    create_excel_file
)
from app.core.models import Chat, ChatMember, DailyRecord, Fine


def test_expected_report_count_week_mix():
    start = date(2026, 2, 2)
    end = date(2026, 2, 8)
    assert expected_report_count(start, end) == 13


def test_completed_report_count_weekday_and_sunday():
    records = [
        DailyRecord(date="2026-02-03", morning_hashtag="1", evening_hashtag="0", week_hashtag="0"),
        DailyRecord(date="2026-02-08", morning_hashtag="0", evening_hashtag="0", week_hashtag="1")
    ]
    assert completed_report_count(records) == 2


def test_build_date_range_empty_on_invalid():
    assert build_date_range(None, date(2026, 2, 1)) == []
    assert build_date_range(date(2026, 2, 2), date(2026, 2, 1)) == []


def test_day_completion_weekday_partial():
    record = DailyRecord(date="2026-02-03", morning_hashtag="1", evening_hashtag="0", week_hashtag="0")
    expected, completed = day_completion(record, date(2026, 2, 3))
    assert expected == 2
    assert completed == 1


def test_calculate_member_metrics_streaks():
    date_list = build_date_range(date(2026, 2, 1), date(2026, 2, 4))
    records = [
        DailyRecord(date="2026-02-01", morning_hashtag="0", evening_hashtag="0", week_hashtag="1"),
        DailyRecord(date="2026-02-02", morning_hashtag="1", evening_hashtag="1", week_hashtag="0"),
        DailyRecord(date="2026-02-03", morning_hashtag="1", evening_hashtag="1", week_hashtag="0")
    ]
    record_by_date, metrics = calculate_member_metrics(records, date_list)
    assert record_by_date
    assert metrics["best_streak"] == 3
    assert metrics["current_streak"] == 0


def test_create_excel_file_has_expected_sheets(session_factory):
    session = session_factory()
    chat = Chat(id=-1001, start_date="2026-02-01")
    member = ChatMember(chat_id=-1001, user_id=1, user_name="user", full_name="User One")
    session.add(chat)
    session.add(member)
    session.commit()
    record = DailyRecord(chat_member_id=member.id, date="2026-02-02",
                         morning_hashtag="1", evening_hashtag="1", week_hashtag="0")
    fine = Fine(chat_member_id=member.id, date_paid="2026-02-03", report_type="morning", fine_amount=10)
    session.add(record)
    session.add(fine)
    session.commit()
    chat_id = chat.id
    session.close()

    workbook = create_excel_file(chat_id)
    sheet_names = workbook.sheetnames
    assert "Overview" in sheet_names
    assert "Leaderboard" in sheet_names
    assert "Trends" in sheet_names
    assert "Heatmap" in sheet_names
    assert "Daily Records" in sheet_names
    assert "Fines" in sheet_names
