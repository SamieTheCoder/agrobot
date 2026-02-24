FROM python:3.11-slim

# Install Chromium from apt (already matched to chromedriver — no version mismatch)
RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
