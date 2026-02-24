FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    wget \
    curl \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Print exact paths so you can see them in Coolify build logs
RUN echo "=== Chromium paths ===" \
    && which chromium || which chromium-browser || echo "NOT FOUND" \
    && which chromedriver || echo "chromedriver NOT FOUND" \
    && chromium --version || chromium-browser --version || echo "version check failed" \
    && chromedriver --version || echo "chromedriver version check failed"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
