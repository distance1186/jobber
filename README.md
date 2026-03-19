# Jobber

Self-hosted job aggregation and tracking system powered by a local LLM agent.

## What it does

- **Scrapes** job listings from LinkedIn and Dice on a schedule
- **Classifies** each job using a local LLM (via Ollama) — scores relevance, extracts skills, generates summaries
- **Stores** everything in PostgreSQL with deduplication
- **Displays** a web dashboard (forked [JobSync](https://github.com/Gsync/jobsync)) to track application status and notes
- **Notifies** you when high-relevance matches are found

Everything runs locally — no cloud APIs required.

## Requirements

- Docker & Docker Compose
- NVIDIA GPU recommended (works on CPU, just slower)
- 8 GB RAM minimum, 16+ GB recommended
- **Firefox is the preferred browser** — the LinkedIn cookie setup script can auto-extract your session cookie from Firefox with zero manual steps

## Quick Start

```bash
# Clone
git clone https://github.com/distance1186/jobber.git
cd jobber

# Configure
cp .env.example .env
# Edit .env with your settings (database password, LinkedIn cookie, etc.)

# Launch
docker compose up -d

# Pull the LLM model (first time only, ~4.7 GB)
docker exec jobber-ollama ollama pull llama3.3

# Check status
docker compose ps

# View dashboard
# Open http://localhost:3000
```

## Recommended Models by System Specs

| RAM | GPU | Recommended Model | Command |
|-----|-----|-------------------|---------|
| <8 GB | None | Phi-4-mini (3.8B) | `ollama pull phi4-mini` |
| 8-16 GB | None | Mistral Small 3 (7B) | `ollama pull mistral-small3` |
| 16-32 GB | 8 GB+ | Llama 3.3 8B | `ollama pull llama3.3` |
| 32+ GB | 12 GB+ | Gemma 3 12B | `ollama pull gemma3:12b` |

Set your model in `.env` via the `OLLAMA_MODEL` variable.

## Architecture

```
┌── Docker Compose Stack ──────────────────────────┐
│  Ollama (LLM)  │  Postgres  │  Agent  │  Dashboard │
│  :11434        │  internal  │  cron   │  :3000     │
└──────────────────────────────────────────────────┘
```

## LinkedIn Cookie Setup

The LinkedIn scraper requires an authenticated session cookie (`li_at`). A helper script can extract it automatically from Firefox:

```bash
python scripts/get-linkedin-cookie.py
```

If you use Firefox and are logged into LinkedIn, the cookie is detected and saved to `.env` automatically. Chrome/Edge users will be guided through a quick manual copy from DevTools.

After updating the cookie, restart the agent:

```bash
docker compose up -d agent
```

## Configuration

Edit `agent/config.yaml` to customize search queries, and `.env` for credentials and model selection.

## License

MIT
