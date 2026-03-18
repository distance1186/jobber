FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    cron curl chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set up log directory
RUN mkdir -p /var/log/job-tracker

# Cron job is mounted via docker-compose volume at /etc/cron.d/job-tracker

# Entrypoint: start cron in foreground
# For development/testing, override with: docker compose exec agent python main.py
CMD ["cron", "-f"]
