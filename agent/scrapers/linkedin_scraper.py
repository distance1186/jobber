"""LinkedIn job scraper using linkedin-jobs-scraper library."""

import json
import logging
import os
import time
from typing import Optional

from linkedin_jobs_scraper import LinkedinScraper
from linkedin_jobs_scraper.events import EventData, Events
from linkedin_jobs_scraper.filters import RelevanceFilters, TimeFilters, TypeFilters
from linkedin_jobs_scraper.query import Query, QueryFilters, QueryOptions

logger = logging.getLogger(__name__)


class LinkedInScraper:
    """Scrapes job listings from LinkedIn using authenticated session cookie."""

    def __init__(self):
        self.li_at_cookie = os.environ.get("LI_AT_COOKIE", "")
        self.jobs: list[dict] = []
        self.rate_limit_delay = 1.5  # seconds between requests

    def _on_data(self, data: EventData):
        """Callback for each scraped job listing."""
        job = {
            "job_id": f"linkedin_{data.job_id}" if data.job_id else f"linkedin_{hash(data.link)}",
            "source": "linkedin",
            "title": data.title,
            "company": data.company,
            "location": data.place,
            "remote": "remote" in (data.place or "").lower(),
            "url": data.link,
            "description": data.description,
            "date_posted": data.date,
            "raw_data": {
                "company_link": data.company_link,
                "insights": data.insights,
            },
        }
        self.jobs.append(job)
        logger.info(f"Scraped: {job['title']} at {job['company']}")

    def _on_error(self, error):
        logger.error(f"LinkedIn scraper error: {error}")

    def _on_end(self):
        logger.info(f"LinkedIn scraping complete. Total jobs: {len(self.jobs)}")

    def scrape(self, queries: list[dict], max_results: int = 50) -> list[dict]:
        """
        Scrape LinkedIn job listings based on search queries.

        Args:
            queries: List of dicts with 'keywords' and 'location' keys.
            max_results: Maximum number of results per query.

        Returns:
            List of normalized job record dicts.
        """
        self.jobs = []

        scraper = LinkedinScraper(
            chrome_executable_path=None,  # auto-detect
            chrome_options=None,
            headless=True,
            max_workers=1,
            slow_mo=self.rate_limit_delay,
            page_load_timeout=40,
        )

        scraper.on(Events.DATA, self._on_data)
        scraper.on(Events.ERROR, self._on_error)
        scraper.on(Events.END, self._on_end)

        linkedin_queries = []
        for q in queries:
            filters = QueryFilters(
                relevance=RelevanceFilters.RELEVANT,
                time=TimeFilters.WEEK,
            )
            if q.get("remote_only"):
                filters.type = [TypeFilters.REMOTE]

            linkedin_queries.append(
                Query(
                    query=q["keywords"],
                    options=QueryOptions(
                        locations=[q.get("location", "United States")],
                        limit=max_results,
                        filters=filters,
                    ),
                )
            )

        scraper.run(linkedin_queries)
        return self.jobs
