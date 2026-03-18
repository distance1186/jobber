"""Notification system using Apprise for multi-backend alerts."""

import logging
import os

import apprise

logger = logging.getLogger(__name__)


def send_notification(job: dict) -> bool:
    """
    Send a notification for a high-relevance job match.

    Args:
        job: Dict with keys: title, company, location, relevance_score,
             llm_summary, url, source.

    Returns:
        True if notification was sent successfully, False otherwise.
    """
    notify_urls = os.environ.get("NOTIFY_URLS", "")
    if not notify_urls:
        logger.debug("No NOTIFY_URLS configured, skipping notification")
        return False

    min_score = int(os.environ.get("NOTIFY_MIN_SCORE", "7"))
    if job.get("relevance_score", 0) < min_score:
        logger.debug(f"Job score {job.get('relevance_score')} below threshold {min_score}")
        return False

    title = f"New Job Match: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}"
    body = (
        f"**Relevance:** {job.get('relevance_score', '?')}/10\n"
        f"**Location:** {job.get('location', 'Unknown')}\n"
        f"**Source:** {job.get('source', 'Unknown')}\n\n"
        f"**Summary:**\n{job.get('llm_summary', 'No summary available')}\n\n"
        f"**Link:** {job.get('url', '')}"
    )

    ap = apprise.Apprise()
    for url in notify_urls.split(","):
        url = url.strip()
        if url:
            ap.add(url)

    try:
        result = ap.notify(title=title, body=body)
        if result:
            logger.info(f"Notification sent for: {job.get('title')}")
        else:
            logger.warning(f"Notification failed for: {job.get('title')}")
        return result
    except Exception as e:
        logger.error(f"Notification error: {e}")
        return False
