"""SQLAlchemy ORM models for the Jobber database."""

import os
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Integer, String, Text, create_engine
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(128), unique=True, nullable=False)
    source = Column(String(32), nullable=False)  # 'linkedin', 'dice'
    title = Column(String(256))
    company = Column(String(256))
    location = Column(String(256))
    remote = Column(Boolean, default=False)
    url = Column(Text)
    description = Column(Text)
    llm_summary = Column(Text)
    relevance_score = Column(Integer, default=0)
    skills = Column(ARRAY(Text))
    date_posted = Column(Date)
    date_scraped = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    date_applied = Column(Date)
    status = Column(String(32), default="new")
    notes = Column(Text)
    raw_data = Column(JSONB)

    def __repr__(self):
        return f"<Job(job_id={self.job_id!r}, title={self.title!r}, company={self.company!r})>"


def get_engine():
    """Create a SQLAlchemy engine from the DATABASE_URL environment variable."""
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://jobtracker:changeme@localhost:5432/jobtracking"
    )
    return create_engine(database_url)


def get_session():
    """Create a new database session."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
