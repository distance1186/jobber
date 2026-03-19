"""Jobber Pipeline Orchestrator.

Loads configuration, runs scrapers, classifies jobs via LLM,
persists to database, and sends notifications for high-relevance matches.
"""

import json
import logging
import os
from datetime import datetime, timezone

import yaml
from dotenv import load_dotenv

from db.models import Job, get_session
from notifications import send_notification
from scrapers.dice_scraper import DiceScraper
from scrapers.linkedin_scraper import LinkedInScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("jobber")

# Load environment variables
load_dotenv()


def load_config(config_path: str = "/app/config.yaml") -> dict:
    """Load the agent configuration file."""
    # Fall back to local path for development
    if not os.path.exists(config_path):
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def run_scrapers(config: dict) -> list[dict]:
    """Run all enabled scrapers and return combined job listings."""
    all_jobs = []
    sources = config.get("sources", {})

    # LinkedIn
    if sources.get("linkedin", {}).get("enabled", False):
        logger.info("Starting LinkedIn scraper...")
        try:
            scraper = LinkedInScraper()
            queries = sources["linkedin"].get("search_queries", [])
            jobs = scraper.scrape(queries)
            all_jobs.extend(jobs)
            logger.info(f"LinkedIn: scraped {len(jobs)} jobs")
        except Exception as e:
            logger.error(f"LinkedIn scraper failed: {e}")

    # Dice
    if sources.get("dice", {}).get("enabled", False):
        logger.info("Starting Dice scraper...")
        try:
            scraper = DiceScraper()
            queries = sources["dice"].get("search_queries", [])
            jobs = scraper.scrape(queries)
            all_jobs.extend(jobs)
            logger.info(f"Dice: scraped {len(jobs)} jobs")
        except Exception as e:
            logger.error(f"Dice scraper failed: {e}")

    logger.info(f"Total jobs scraped: {len(all_jobs)}")
    return all_jobs


def classify_job(job: dict) -> dict:
    """Use the local LLM to classify a single job.

    This is a simplified version that calls Ollama directly.
    The full CrewAI pipeline in agent_crew.py provides more
    sophisticated multi-agent classification.
    """
    import requests

    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.environ.get("OLLAMA_MODEL", "llama3.3")
    role_context = os.environ.get(
        "JOB_ROLE_CONTEXT",
        "Senior Systems Administrator with 20+ years Linux/Windows experience"
    )

    prompt = f"""You are a job relevance classifier. Given a job posting, evaluate it for a {role_context}.

Job Title: {job.get('title', 'Unknown')}
Company: {job.get('company', 'Unknown')}
Location: {job.get('location', 'Unknown')}
Description (first 2000 chars): {(job.get('description', '') or '')[:2000]}

Respond in this exact JSON format (no other text):
{{
  "relevance_score": <1-10 integer>,
  "llm_summary": "• bullet 1\\n• bullet 2\\n• bullet 3",
  "skills": ["skill1", "skill2", "skill3"]
}}"""

    try:
        resp = requests.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        result_text = resp.json().get("response", "")

        # Try to parse JSON from the response
        # Strip markdown code fences if present
        cleaned = result_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0]

        result = json.loads(cleaned)
        job["relevance_score"] = max(1, min(10, int(result.get("relevance_score", 0))))
        job["llm_summary"] = result.get("llm_summary", "")
        job["skills"] = result.get("skills", [])
        logger.info(f"Classified: {job['title']} → score {job['relevance_score']}")
    except Exception as e:
        logger.warning(f"Classification failed for {job.get('title', '?')}: {e}")
        job["relevance_score"] = 0
        job["llm_summary"] = "Classification failed"
        job["skills"] = []

    return job


def persist_jobs(jobs: list[dict]) -> dict:
    """Persist classified jobs to the database, deduplicating by job_id.

    Returns a summary dict with counts of new, updated, and skipped jobs.
    """
    session = get_session()
    stats = {"new": 0, "updated": 0, "skipped": 0, "high_relevance": []}

    try:
        for job in jobs:
            existing = session.query(Job).filter_by(job_id=job["job_id"]).first()

            if existing:
                # Update if description changed
                if existing.description != job.get("description"):
                    existing.description = job.get("description")
                    existing.llm_summary = job.get("llm_summary")
                    existing.relevance_score = job.get("relevance_score", 0)
                    existing.skills = job.get("skills", [])
                    existing.raw_data = job.get("raw_data")
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
            else:
                new_job = Job(
                    job_id=job["job_id"],
                    source=job.get("source", "unknown"),
                    title=job.get("title"),
                    company=job.get("company"),
                    location=job.get("location"),
                    remote=job.get("remote", False),
                    url=job.get("url"),
                    description=job.get("description"),
                    llm_summary=job.get("llm_summary"),
                    relevance_score=job.get("relevance_score", 0),
                    skills=job.get("skills", []),
                    date_posted=job.get("date_posted") or None,
                    raw_data=job.get("raw_data"),
                    status="new",
                )
                session.add(new_job)
                stats["new"] += 1

                # Track high-relevance for notifications
                min_score = int(os.environ.get("NOTIFY_MIN_SCORE", "7"))
                if job.get("relevance_score", 0) >= min_score:
                    stats["high_relevance"].append(job)

        session.commit()
        logger.info(
            f"Database: {stats['new']} new, {stats['updated']} updated, "
            f"{stats['skipped']} skipped, {len(stats['high_relevance'])} high-relevance"
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        session.close()

    return stats


def main():
    """Run the full Jobber pipeline."""
    logger.info("=" * 60)
    logger.info("Jobber Pipeline Started")
    logger.info("=" * 60)

    start_time = datetime.now(timezone.utc)

    # Load config
    config = load_config()

    # Step 1: Scrape
    logger.info("Step 1/4: Scraping job listings...")
    jobs = run_scrapers(config)

    if not jobs:
        logger.info("No jobs scraped. Pipeline complete.")
        return

    # Step 2: Classify each job via LLM
    logger.info("Step 2/4: Classifying jobs via LLM...")
    classified_jobs = []
    for job in jobs:
        classified = classify_job(job)
        classified_jobs.append(classified)

    # Step 3: Persist to database
    logger.info("Step 3/4: Persisting to database...")
    stats = persist_jobs(classified_jobs)

    # Step 4: Send notifications for high-relevance matches
    logger.info("Step 4/4: Sending notifications...")
    for job in stats.get("high_relevance", []):
        send_notification(job)

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(f"Pipeline complete in {elapsed:.1f}s")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
