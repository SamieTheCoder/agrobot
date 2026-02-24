FROM python:3.11-slim

# Install Chromium + chromedriver from Debian repos (versions always match)
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    wget \
    curl \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Confirm paths exist (helps debug if wrong)
RUN which chromium && which chromedriver && echo "✅ Chromium ready"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
