"""Tests for database persistence and deduplication logic."""

import os
import pytest
from unittest.mock import patch, MagicMock

from db.models import Job, Base


def make_job_dict(**overrides):
    """Create a test job dict with sensible defaults."""
    defaults = {
        "job_id": "test_123",
        "source": "dice",
        "title": "Linux Admin",
        "company": "TestCorp",
        "location": "Remote",
        "remote": True,
        "url": "https://example.com/job/123",
        "description": "Manage Linux servers.",
        "llm_summary": "• Linux admin role\n• Remote position\n• Requires 5+ years",
        "relevance_score": 7,
        "skills": ["linux", "docker"],
        "date_posted": None,
        "raw_data": {"source_id": "123"},
        "status": "new",
    }
    defaults.update(overrides)
    return defaults


class TestJobModel:
    """Tests for the Job SQLAlchemy model."""

    def test_job_repr(self):
        job = Job(job_id="test_1", title="Admin", company="Corp")
        assert "test_1" in repr(job)
        assert "Admin" in repr(job)

    def test_job_status_column_has_default(self):
        """Verify the status column is configured with 'new' as default."""
        col = Job.__table__.columns["status"]
        assert col.default.arg == "new"

    def test_job_relevance_column_has_default(self):
        """Verify the relevance_score column is configured with 0 as default."""
        col = Job.__table__.columns["relevance_score"]
        assert col.default.arg == 0


class TestDeduplication:
    """Tests for the persist_jobs deduplication logic in main.py."""

    @patch("main.get_session")
    @patch("main.os.environ.get", return_value="7")
    def test_new_job_inserted(self, mock_env, mock_session):
        """A job with a new job_id should be inserted."""
        from main import persist_jobs

        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = None
        mock_session.return_value = session

        job = make_job_dict(job_id="new_job_001")
        stats = persist_jobs([job])

        assert stats["new"] == 1
        assert stats["skipped"] == 0
        assert stats["updated"] == 0
        session.add.assert_called_once()
        session.commit.assert_called_once()

    @patch("main.get_session")
    @patch("main.os.environ.get", return_value="7")
    def test_duplicate_job_skipped(self, mock_env, mock_session):
        """A job with the same job_id and same description should be skipped."""
        from main import persist_jobs

        existing = MagicMock()
        existing.description = "Manage Linux servers."  # same as default
        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = existing
        mock_session.return_value = session

        job = make_job_dict()
        stats = persist_jobs([job])

        assert stats["skipped"] == 1
        assert stats["new"] == 0
        session.add.assert_not_called()

    @patch("main.get_session")
    @patch("main.os.environ.get", return_value="7")
    def test_changed_job_updated(self, mock_env, mock_session):
        """A job with the same job_id but different description should be updated."""
        from main import persist_jobs

        existing = MagicMock()
        existing.description = "Old description"  # different from default
        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = existing
        mock_session.return_value = session

        job = make_job_dict()
        stats = persist_jobs([job])

        assert stats["updated"] == 1
        assert existing.description == "Manage Linux servers."

    @patch("main.get_session")
    @patch("main.os.environ.get", return_value="7")
    def test_high_relevance_tracked(self, mock_env, mock_session):
        """New jobs with relevance >= threshold should be in high_relevance list."""
        from main import persist_jobs

        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = None
        mock_session.return_value = session

        job = make_job_dict(relevance_score=9)
        stats = persist_jobs([job])

        assert len(stats["high_relevance"]) == 1
        assert stats["high_relevance"][0]["relevance_score"] == 9

    @patch("main.get_session")
    @patch("main.os.environ.get", return_value="7")
    def test_low_relevance_not_tracked(self, mock_env, mock_session):
        """New jobs with relevance < threshold should not be in high_relevance."""
        from main import persist_jobs

        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = None
        mock_session.return_value = session

        job = make_job_dict(relevance_score=3)
        stats = persist_jobs([job])

        assert len(stats["high_relevance"]) == 0
