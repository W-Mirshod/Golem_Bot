FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed for golemsp
RUN apt-get update && apt-get install -y \
    curl \
    bash \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY bot.py .

# Copy platforms module
COPY platforms/ platforms/

# Note: GolemSP needs to be installed separately or mounted from host
# If golemsp is installed on the host, you may need to:
# 1. Mount the golemsp binary: -v /usr/local/bin/golemsp:/usr/local/bin/golemsp
# 2. Or install golemsp in the container (add installation steps here)

# Run yagna service and bot
# Start yagna service in background, then start the bot
CMD ["/bin/bash", "-c", "yagna service run & sleep 5 && python bot.py"]

