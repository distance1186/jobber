"""Tests for LLM classification logic."""

import json
import pytest
from unittest.mock import patch, MagicMock


class TestClassifyJob:
    """Tests for the classify_job function in main.py."""

    @patch("requests.post")
    def test_successful_classification(self, mock_post):
        """Verify classify_job parses a valid LLM JSON response."""
        from main import classify_job

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": json.dumps({
                "relevance_score": 8,
                "llm_summary": "• Good match\n• Remote\n• Linux focus",
                "skills": ["linux", "docker", "aws"],
            })
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        job = {
            "title": "Senior Linux Admin",
            "company": "TestCorp",
            "location": "Remote",
            "description": "Manage Linux servers with Docker and AWS.",
        }
        result = classify_job(job)

        assert result["relevance_score"] == 8
        assert "Good match" in result["llm_summary"]
        assert "linux" in result["skills"]

    @patch("requests.post")
    def test_classification_with_code_fences(self, mock_post):
        """Verify classify_job strips markdown code fences from LLM output."""
        from main import classify_job

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": '```json\n{"relevance_score": 6, "llm_summary": "OK match", "skills": ["python"]}\n```'
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        job = {"title": "Dev", "company": "Co", "location": "NYC", "description": "Python dev role"}
        result = classify_job(job)

        assert result["relevance_score"] == 6
        assert result["skills"] == ["python"]

    @patch("requests.post")
    def test_score_clamped_to_range(self, mock_post):
        """Verify relevance_score is clamped between 1 and 10."""
        from main import classify_job

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": json.dumps({
                "relevance_score": 15,  # out of range
                "llm_summary": "Overscored",
                "skills": [],
            })
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        job = {"title": "Admin", "company": "Co", "location": "NYC", "description": "Test"}
        result = classify_job(job)
        assert result["relevance_score"] == 10  # clamped to max

    @patch("requests.post")
    def test_classification_failure_returns_defaults(self, mock_post):
        """Verify classify_job sets defaults when LLM call fails."""
        from main import classify_job

        mock_post.side_effect = Exception("Ollama unreachable")

        job = {"title": "Admin", "company": "Co", "location": "NYC", "description": "Test"}
        result = classify_job(job)

        assert result["relevance_score"] == 0
        assert result["llm_summary"] == "Classification failed"
        assert result["skills"] == []

    @patch("requests.post")
    def test_classification_bad_json_returns_defaults(self, mock_post):
        """Verify classify_job handles non-JSON LLM response."""
        from main import classify_job

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": "I cannot provide a JSON response for this job."
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        job = {"title": "Admin", "company": "Co", "location": "NYC", "description": "Test"}
        result = classify_job(job)

        assert result["relevance_score"] == 0
        assert result["llm_summary"] == "Classification failed"

    @patch("requests.post")
    def test_truncates_long_descriptions(self, mock_post):
        """Verify long descriptions are truncated to 2000 chars in the prompt."""
        from main import classify_job

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": json.dumps({
                "relevance_score": 5,
                "llm_summary": "Average match",
                "skills": [],
            })
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        long_desc = "x" * 5000
        job = {"title": "Admin", "company": "Co", "location": "NYC", "description": long_desc}
        classify_job(job)

        # Check the prompt sent to Ollama doesn't contain full 5000 chars
        call_body = mock_post.call_args.kwargs.get("json", mock_post.call_args[1].get("json", {}))
        prompt = call_body.get("prompt", "")
        # The description in the prompt should be truncated
        assert len(prompt) < 5000
