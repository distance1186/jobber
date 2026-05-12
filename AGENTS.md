# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## What This Project Is

Jobber is a self-hosted job aggregation and tracking system. It scrapes LinkedIn and Dice, classifies each listing with a local LLM (Ollama), stores results in PostgreSQL, and surfaces them in a web dashboard (forked JobSync). Everything runs in Docker with no cloud APIs required.

## Commands

### Running the Stack

```bash
# Start all services
docker compose up -d

# Pull LLM model (first time only, ~4.7 GB)
docker exec jobber-ollama ollama pull llama3.3

# Trigger the pipeline immediately (instead of waiting for cron)
docker compose exec agent python main.py

# View agent logs
docker compose logs -f agent
```

### Python Agent (agent/)

Tests require `DATABASE_URL` to be set; the dedup tests mock the session but model introspection tests work without a live DB.

```bash
# Run all tests
pytest agent/tests/ -v

# Run a single test file
pytest agent/tests/test_classifier.py -v

# Run a single test by name
pytest agent/tests/test_classifier.py::TestClassifyJob::test_successful_classification -v

# Lint (max line length 120, tests excluded)
flake8 agent/ --max-line-length=120 --exclude=agent/tests
```

### Go CLI (cli/)

```bash
# Vet
cd cli && go vet ./...

# Build for local use
cd cli && go build -o jobber-setup .

# Cross-compile (as done in CI)
cd cli && GOOS=linux GOARCH=amd64 go build -o jobber-setup .
cd cli && GOOS=windows GOARCH=amd64 go build -o jobber-setup.exe .
```

## Architecture

### Services (docker-compose.yml)

| Service | Image | Port | Role |
|---|---|---|---|
| `ollama` | `ollama/ollama` | 11434 | Local LLM inference |
| `postgres` | `postgres:15-alpine` | internal | Job storage |
| `agent` | Built from `agent/Dockerfile` | — | Scrape/classify/persist pipeline (runs via cron) |
| `dashboard` | `ghcr.io/distance1186/jobsync:latest` | 3000 | Web UI |

The agent container runs `cron -f` as its entrypoint. The crontab (`cron/crontab`) is mounted at `/etc/cron.d/job-tracker` and fires `python main.py` at 7AM, 12PM, and 6PM.

### Python Agent Pipeline (`agent/`)

The pipeline is orchestrated by `main.py` in four steps:

1. **Scrape** — `run_scrapers()` calls enabled scrapers from `agent/scrapers/`
   - `LinkedInScraper` uses the `linkedin-jobs-scraper` library (Selenium + Chromium); requires `LI_AT_COOKIE` env var
   - `DiceScraper` hits Dice's public JSON REST API; no auth needed
2. **Classify** — `classify_job()` calls Ollama's `/api/generate` endpoint directly, prompting for a 1–10 relevance score, a 3-bullet summary, and extracted skills. Strips markdown code fences from LLM output before JSON parsing.
3. **Persist** — `persist_jobs()` deduplicates by `job_id`. If a job already exists with the same description it is skipped; if the description changed it is re-classified and updated.
4. **Notify** — `notifications.py` uses Apprise to send alerts for jobs whose `relevance_score >= NOTIFY_MIN_SCORE`.

`agent_crew.py` contains an alternative CrewAI multi-agent pipeline (Scraper → Classifier → Tracker agents) but is **not currently invoked** by `main.py`; it exists for future use.

### Database (`db/init.sql`, `agent/db/models.py`)

Single `jobs` table; the SQLAlchemy model mirrors the schema exactly. Key fields:
- `job_id` (unique) — prefixed by source: `linkedin_<id>` or `dice_<id>`
- `relevance_score` — 1–10 integer from LLM
- `skills` — PostgreSQL `TEXT[]` array
- `raw_data` — full source payload as `JSONB`
- `status` — lifecycle: `new | reviewed | applied | interview | offer | rejected | archived`

### Go CLI (`cli/`)

A Cobra CLI binary (`jobber-setup`) that wraps the Docker Compose stack. Internal packages under `cli/internal/` handle:
- `detect` — hardware detection (RAM, CPU, GPU/VRAM)
- `docker` — `docker compose` subprocess calls (up, down, pull, ps)
- `wizard` — serves a local setup wizard at `:9898/setup`

Commands: `install`, `start`, `stop`, `restart`, `status`, `update`, `config`.

### Configuration

- `.env` — credentials and model selection (copy from `.env.example`)
- `agent/config.yaml` — search queries per source (LinkedIn and Dice), LLM context string, and minimum notification score
- `OLLAMA_MODEL` env var controls which model is used; `llama3.3` is the default

### CI (`.github/workflows/`)

- `lint-test.yml` — runs on PRs to `main`: flake8 lint + pytest (Python), go vet + cross-compile (Go); spins up a real Postgres service container for tests
- `release.yml` — triggered by `v*.*.*` tags; builds Go binaries, `.deb`, `.tar.gz`, Windows Inno Setup installer, and pushes the agent Docker image to GHCR
