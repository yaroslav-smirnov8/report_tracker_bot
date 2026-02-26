import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import load_env_file

load_env_file()
db_url = os.getenv("DB_URL", "mysql+pymysql://root:123@localhost/botdb")

engine = create_engine(
    db_url,
    pool_size=20,
    max_overflow=40
)

Session = sessionmaker(bind=engine)
Base = declarative_base()


def init_db():
    Base.metadata.create_all(engine)
