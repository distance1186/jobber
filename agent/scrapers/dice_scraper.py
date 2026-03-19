"""Dice.com job scraper using their public REST API."""

import logging

import requests

logger = logging.getLogger(__name__)

DICE_API_URL = "https://job-search-api.svc.dhigroupinc.com/v1/dice/jobs/search"


# Dice's frontend API key — used by their web app, publicly visible in browser DevTools.
DICE_API_KEY = "1YAt0R9wBg4WfsF9VB2778F5CHLAPMVW3WAZcKd8"


class DiceScraper:
    """Scrapes job listings from Dice.com via their public JSON API."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Accept": "application/json, text/plain, */*",
            "x-api-key": DICE_API_KEY,
        })

    def scrape(self, queries: list[dict], max_results: int = 50) -> list[dict]:
        """
        Scrape Dice job listings based on search queries.

        Args:
            queries: List of dicts with 'keywords' and optional 'radius_miles', 'remote_only'.
            max_results: Maximum number of results per query.

        Returns:
            List of normalized job record dicts.
        """
        all_jobs = []

        for q in queries:
            try:
                jobs = self._search(
                    keywords=q["keywords"],
                    radius_miles=q.get("radius_miles", 50),
                    remote_only=q.get("remote_only", False),
                    page_size=min(max_results, 50),
                )
                all_jobs.extend(jobs)
                logger.info(f"Dice: scraped {len(jobs)} jobs for '{q['keywords']}'")
            except Exception as e:
                logger.error(f"Dice scraper error for '{q['keywords']}': {e}")

        return all_jobs

    def _search(
        self,
        keywords: str,
        radius_miles: int = 50,
        remote_only: bool = False,
        page_size: int = 50,
        page_num: int = 1,
    ) -> list[dict]:
        """Execute a single search query against the Dice API."""
        params = {
            "q": keywords,
            "countryCode2": "US",
            "radius": radius_miles,
            "radiusUnit": "mi",
            "pageSize": page_size,
            "pageNum": page_num,
            "language": "en",
            "eid": "1",
        }
        if remote_only:
            params["filters.isRemote"] = "true"

        response = self.session.get(DICE_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        jobs = []
        for item in data.get("data", []):
            job = {
                "job_id": f"dice_{item.get('id', '')}",
                "source": "dice",
                "title": item.get("title", ""),
                "company": item.get("companyName", ""),
                "location": item.get("jobLocation", {}).get("displayName", ""),
                "remote": item.get("isRemote", False),
                "url": item.get("detailsPageUrl", f"https://www.dice.com/job-detail/{item.get('id', '')}"),
                "description": item.get("jobDescription", ""),
                "date_posted": item.get("postedDate", ""),
                "raw_data": item,
            }
            jobs.append(job)

        return jobs
