"""CrewAI agent definitions for the Jobber pipeline."""

import os

from crewai import Agent, Crew, Task
from langchain_ollama import OllamaLLM


def get_llm():
    """Initialize the Ollama LLM with the configured model."""
    model = os.environ.get("OLLAMA_MODEL", "llama3.3")
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    return OllamaLLM(model=model, base_url=base_url)


def create_scraper_agent(llm):
    """Agent responsible for scraping job listings from configured sources."""
    return Agent(
        role="Job Scraper",
        goal="Scrape job listings from LinkedIn and Dice based on configured search queries",
        backstory=(
            "Expert at web scraping and data extraction. Handles pagination, "
            "rate limiting, and raw data normalization from multiple job boards."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_classifier_agent(llm):
    """Agent responsible for scoring and summarizing job relevance."""
    job_context = os.environ.get(
        "JOB_ROLE_CONTEXT",
        "Senior Systems Administrator with 20+ years Linux/Windows experience"
    )
    return Agent(
        role="Job Classifier",
        goal=f"Score and summarize job relevance for a {job_context}",
        backstory=(
            "Expert at parsing technical job descriptions. Scores relevance 1-10, "
            "extracts key skills, and generates concise 3-bullet summaries."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_tracker_agent(llm):
    """Agent responsible for database persistence and deduplication."""
    return Agent(
        role="Database Tracker",
        goal="Persist job records, deduplicate by job_id, and trigger notifications",
        backstory=(
            "Expert at database operations and data integrity. Compares incoming "
            "records against existing data, inserts new records, updates changed "
            "records, and fires notifications for high-relevance matches."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_scrape_task(agent, sources_config):
    """Create a scraping task for the given agent and source configuration."""
    return Task(
        description=(
            f"Scrape job listings from the following sources: {sources_config}. "
            "Return a list of normalized job records with fields: job_id, source, "
            "title, company, location, remote, url, description, date_posted, raw_data."
        ),
        expected_output="A JSON list of normalized job records.",
        agent=agent,
    )


def create_classify_task(agent, jobs_data):
    """Create a classification task for scraped jobs."""
    return Task(
        description=(
            f"Classify the following job records: {jobs_data}. "
            "For each job, provide: relevance_score (1-10), llm_summary (3 bullet points), "
            "and skills (list of key technical skills extracted from the description)."
        ),
        expected_output="A JSON list of classified job records with scores, summaries, and skills.",
        agent=agent,
    )


def create_track_task(agent, classified_jobs):
    """Create a tracking task to persist classified jobs to the database."""
    return Task(
        description=(
            f"Process the following classified jobs: {classified_jobs}. "
            "For each job: check if job_id already exists in the database. "
            "Insert new records, update changed records. "
            "Return a summary of new jobs added and any high-relevance matches."
        ),
        expected_output="A summary report of database operations performed.",
        agent=agent,
    )


def run_pipeline(sources_config, jobs_data=None):
    """Execute the full Scraper -> Classifier -> Tracker pipeline."""
    llm = get_llm()

    scraper = create_scraper_agent(llm)
    classifier = create_classifier_agent(llm)
    tracker = create_tracker_agent(llm)

    scrape_task = create_scrape_task(scraper, sources_config)
    classify_task = create_classify_task(classifier, "{scrape_task output}")
    track_task = create_track_task(tracker, "{classify_task output}")

    crew = Crew(
        agents=[scraper, classifier, tracker],
        tasks=[scrape_task, classify_task, track_task],
        verbose=True,
    )

    result = crew.kickoff()
    return result
