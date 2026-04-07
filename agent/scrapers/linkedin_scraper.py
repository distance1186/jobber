"""LinkedIn job scraper using linkedin-jobs-scraper library.

Uses anti-detection measures to mimic human browsing behavior:
- Custom Chrome options that hide automation signals
- Randomized delays between page actions
- Reduced scrape volume per session
- Pauses between queries
"""

import logging
import os
import random
import time

from selenium.webdriver.chrome.options import Options

from linkedin_jobs_scraper import LinkedinScraper
from linkedin_jobs_scraper.events import EventData, Events
from linkedin_jobs_scraper.filters import (
    OnSiteOrRemoteFilters,
    RelevanceFilters,
    TimeFilters,
)
from linkedin_jobs_scraper.query import Query, QueryFilters, QueryOptions

logger = logging.getLogger(__name__)

# Rotate user-agents to avoid fingerprinting on a single string.
_USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
]

# Max jobs per query — keep it modest to avoid triggering rate limits.
_DEFAULT_MAX_RESULTS = 25


def _build_stealth_options() -> Options:
    """Build Chrome options that reduce automation fingerprinting."""
    opts = Options()

    # Headless
    opts.add_argument("--headless=new")

    # Basic stability flags
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--mute-audio")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--remote-allow-origins=*")

    # Realistic window size (not the default 800×600)
    width, height = random.choice([(1920, 1080), (1680, 1050), (1440, 900)])
    opts.add_argument(f"--window-size={width},{height}")

    # Random user-agent
    ua = random.choice(_USER_AGENTS)
    opts.add_argument(f"--user-agent={ua}")

    # ---- Anti-detection flags ----
    # Remove the "Chrome is being controlled by automated software" bar
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    # Disable downloads (same as library default)
    opts.add_experimental_option(
        "prefs",
        {
            "safebrowsing.enabled": "false",
            "download.prompt_for_download": False,
            "download.default_directory": "/dev/null",
            "download_restrictions": 3,
            "profile.default_content_setting_values.notifications": 2,
        },
    )

    return opts


class LinkedInScraper:
    """Scrapes job listings from LinkedIn using authenticated session cookie."""

    def __init__(self):
        self.li_at_cookie = os.environ.get("LI_AT_COOKIE", "")
        self.jobs: list[dict] = []

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

    def scrape(self, queries: list[dict], max_results: int = _DEFAULT_MAX_RESULTS) -> list[dict]:
        """
        Scrape LinkedIn job listings based on search queries.

        Args:
            queries: List of dicts with 'keywords' and 'location' keys.
            max_results: Maximum number of results per query (default 25).

        Returns:
            List of normalized job record dicts.
        """
        self.jobs = []

        # Randomized delay between page actions (3-6 seconds)
        slow_mo = round(random.uniform(3.0, 6.0), 1)

        scraper = LinkedinScraper(
            chrome_executable_path=None,
            chrome_options=_build_stealth_options(),
            headless=True,
            max_workers=1,
            slow_mo=slow_mo,
            page_load_timeout=40,
        )

        # Library checks isinstance(cb, FunctionType) which rejects bound methods.
        # Wrap in lambdas to work around this.
        scraper.on(Events.DATA, lambda data: self._on_data(data))
        scraper.on(Events.ERROR, lambda error: self._on_error(error))
        scraper.on(Events.END, lambda: self._on_end())

        # Run each query separately with a human-like pause between them
        for i, q in enumerate(queries):
            if i > 0:
                pause = random.uniform(30, 60)
                logger.info(f"Pausing {pause:.0f}s between queries...")
                time.sleep(pause)

            filters = QueryFilters(
                relevance=RelevanceFilters.RELEVANT,
                time=TimeFilters.WEEK,
            )
            if q.get("remote_only"):
                filters.on_site_or_remote = [OnSiteOrRemoteFilters.REMOTE]

            query = Query(
                query=q["keywords"],
                options=QueryOptions(
                    locations=[q.get("location", "United States")],
                    limit=max_results,
                    filters=filters,
                ),
            )

            scraper.run([query])

        return self.jobs
