import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.db import Base
from app.core import db as core_db
from app.reports import excel_reports
from app.services import settings_service


@pytest.fixture()
def session_factory(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(core_db, "Session", TestingSession)
    monkeypatch.setattr(excel_reports, "Session", TestingSession)
    monkeypatch.setattr(settings_service, "Session", TestingSession)
    return TestingSession
