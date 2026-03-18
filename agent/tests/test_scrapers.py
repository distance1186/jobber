"""Tests for job scraper modules."""

import pytest
from unittest.mock import patch, MagicMock

from scrapers.dice_scraper import DiceScraper, DICE_API_URL, DICE_API_KEY


class TestDiceScraper:
    """Tests for the Dice.com REST API scraper."""

    def test_init_sets_required_headers(self):
        scraper = DiceScraper()
        assert "x-api-key" in scraper.session.headers
        assert scraper.session.headers["x-api-key"] == DICE_API_KEY
        assert "User-Agent" in scraper.session.headers

    @patch("scrapers.dice_scraper.requests.Session.get")
    def test_scrape_returns_normalized_jobs(self, mock_get):
        """Verify scraper normalizes Dice API response into our schema."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "abc123",
                    "title": "Senior Linux Admin",
                    "companyName": "TestCorp",
                    "jobLocation": {"displayName": "Remote, USA"},
                    "isRemote": True,
                    "jobDescription": "Manage Linux servers...",
                    "postedDate": "2026-03-15",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = DiceScraper()
        jobs = scraper.scrape([{"keywords": "linux admin"}], max_results=5)

        assert len(jobs) == 1
        job = jobs[0]
        assert job["job_id"] == "dice_abc123"
        assert job["source"] == "dice"
        assert job["title"] == "Senior Linux Admin"
        assert job["company"] == "TestCorp"
        assert job["remote"] is True
        assert "dice.com/job-detail/abc123" in job["url"]

    @patch("scrapers.dice_scraper.requests.Session.get")
    def test_scrape_handles_empty_response(self, mock_get):
        """Verify scraper handles empty API response gracefully."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = DiceScraper()
        jobs = scraper.scrape([{"keywords": "nonexistent job"}])
        assert jobs == []

    @patch("scrapers.dice_scraper.requests.Session.get")
    def test_scrape_handles_api_error(self, mock_get):
        """Verify scraper catches exceptions and returns empty list."""
        mock_get.side_effect = Exception("Connection timeout")

        scraper = DiceScraper()
        jobs = scraper.scrape([{"keywords": "linux admin"}])
        assert jobs == []

    @patch("scrapers.dice_scraper.requests.Session.get")
    def test_scrape_remote_filter(self, mock_get):
        """Verify remote_only filter is passed to API params."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = DiceScraper()
        scraper.scrape([{"keywords": "sysadmin", "remote_only": True}])

        call_args = mock_get.call_args
        params = call_args.kwargs.get("params", call_args[1].get("params", {}))
        assert params.get("filters.isRemote") == "true"

    @patch("scrapers.dice_scraper.requests.Session.get")
    def test_scrape_multiple_queries(self, mock_get):
        """Verify scraper runs all queries and combines results."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"id": "job1", "title": "Admin", "companyName": "Co",
                       "jobLocation": {"displayName": "NYC"}, "isRemote": False,
                       "jobDescription": "desc", "postedDate": "2026-03-15"}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = DiceScraper()
        jobs = scraper.scrape([
            {"keywords": "linux admin"},
            {"keywords": "sysadmin"},
        ])
        assert len(jobs) == 2  # one result per query
        assert mock_get.call_count == 2
