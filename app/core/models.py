from sqlalchemy import Column, Integer, String, ForeignKey, BigInteger, Index
from app.core.db import Base
from app.core.config import DEFAULT_TIMEZONE


class Chat(Base):
    __tablename__ = 'chats'
    id = Column(BigInteger, primary_key=True)
    start_date = Column(String(255))


class ChatMember(Base):
    __tablename__ = 'members'
    # Indexes support frequent lookups by chat and user for message processing.
    __table_args__ = (
        Index('ix_members_chat_id', 'chat_id'),
        Index('ix_members_chat_user', 'chat_id', 'user_id'),
    )
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, ForeignKey('chats.id', ondelete='CASCADE'))
    user_id = Column(BigInteger, nullable=False)
    user_name = Column(String(255))
    full_name = Column(String(255))


class DailyRecord(Base):
    __tablename__ = 'daily_records'
    # Date-based indexes keep daily report checks fast at scale.
    __table_args__ = (
        Index('ix_daily_records_date', 'date'),
        Index('ix_daily_records_member_date', 'chat_member_id', 'date'),
    )
    id = Column(Integer, primary_key=True)
    chat_member_id = Column(Integer, ForeignKey('members.id', ondelete='CASCADE'))
    date = Column(String(255))
    # Flags are stored as "1"/"0" to keep SQL filters consistent across reminders.
    morning_hashtag = Column(String(255), default="0")
    evening_hashtag = Column(String(255), default="0")
    week_hashtag = Column(String(255), default="0")


class Settings(Base):
    __tablename__ = 'settings'
    # Settings are stored per chat; the unique index enforces one row per chat.
    __table_args__ = (
        Index('ix_settings_chat_id', 'chat_id'),
    )
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False)
    morning_hashtag = Column(String(255), default="#morning")
    evening_hashtag = Column(String(255), default="#evening")
    week_hashtag = Column(String(255), default="#week")
    morning_deadline = Column(String(255), default="10:00")
    evening_deadline = Column(String(255), default="23:59")
    start_date = Column(String(255), nullable=True)
    timezone = Column(String(64), default=DEFAULT_TIMEZONE)


class UserState(Base):
    __tablename__ = 'user_states'
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    state = Column(String(255))
    data = Column(String(255), nullable=True)


class Fine(Base):
    __tablename__ = 'fines'
    id = Column(Integer, primary_key=True)
    chat_member_id = Column(Integer, ForeignKey('members.id'))
    date_paid = Column(String(255))
    report_type = Column(String(255))
    fine_amount = Column(Integer, nullable=True)


class HomeworkScore(Base):
    __tablename__ = 'homework_scores'
    id = Column(Integer, primary_key=True)
    chat_member_id = Column(Integer, ForeignKey('members.id', ondelete='CASCADE'))
    assignment_date = Column(String(255))
    score = Column(Integer, nullable=True)
    max_score = Column(Integer, nullable=True)
