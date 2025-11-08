# GolemSP Status Telegram Bot

A Telegram bot that allows you to check the status of your GolemSP service with a simple button click.

## Features

- Check GolemSP status via inline keyboard button
- Direct `/status` command support
- Formatted status output with all service information
- Error handling for service issues

## Prerequisites

- Python 3.8 or higher
- GolemSP installed and accessible via `golemsp` command
- A Telegram bot token

## Setup

### 1. Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to choose a name and username for your bot
4. BotFather will provide you with a token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
5. Save this token - you'll need it in the next step

### 2. Install Dependencies

```bash
# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 3. Configure the Bot

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Telegram bot token:
   ```
   BOT_TOKEN=your_telegram_bot_token_here
   ```

   Replace `your_telegram_bot_token_here` with the token you received from BotFather.

### 4. Run the Bot

```bash
python bot.py
```

The bot will start and you should see:
```
Starting GolemSP Status Bot...
```

## Usage

1. Open Telegram and search for your bot (using the username you set with BotFather)
2. Send `/start` to begin
3. Click the "Check GolemSP Status" button to get the current status
4. Alternatively, use `/status` command directly

## Status Information

The bot displays the following information:
- Service status (running/stopped)
- Version, Commit, Date, Build
- Node Name, Subnet, VM status
- Driver status
- Wallet address and balance (on-chain and polygon)
- Task statistics (processed, in progress, etc.)

## Troubleshooting

### Bot doesn't respond
- Check that the bot token is correct in `.env` file
- Ensure the bot is running (check console for errors)
- Verify you're messaging the correct bot

### "golemsp command not found" error
- Ensure GolemSP is installed
- Verify `golemsp` is in your PATH
- Try running `golemsp status` manually in terminal

### Command timeout
- The bot has a 30-second timeout for the status command
- If GolemSP is slow to respond, you may need to increase the timeout in `bot.py`

## Docker Compose Setup

### Prerequisites

- Docker and Docker Compose installed
- GolemSP installed on the host system (or in another container)

### Quick Start

1. Create `.env` file with your bot token:
   ```bash
   echo "BOT_TOKEN=your_telegram_bot_token_here" > .env
   ```

2. Build and start the container:
   ```bash
   docker compose up -d
   ```

3. View logs:
   ```bash
   docker compose logs -f
   ```

4. Stop the bot:
   ```bash
   docker compose down
   ```

### Configuration

The `docker-compose.yml` file is configured to:
- Mount the `golemsp` binary from the host system (default: `/usr/local/bin/golemsp`)
- Use host networking to access GolemSP service
- Automatically restart the container if it stops

**Note:** If your `golemsp` binary is in a different location, update the volume mount in `docker-compose.yml`:
```yaml
volumes:
  - /path/to/your/golemsp:/usr/local/bin/golemsp:ro
```

### Using Podman

If you prefer Podman instead of Docker:
```bash
podman-compose up -d
```

Or with Podman's native compose support:
```bash
podman compose up -d
```

## Running as a Service

To run the bot as a systemd service, create a service file:

```ini
[Unit]
Description=GolemSP Status Telegram Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/mer/W_Mirshod/Golem_Bot
Environment="PATH=/home/mer/W_Mirshod/Golem_Bot/venv/bin"
ExecStart=/home/mer/W_Mirshod/Golem_Bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save it as `/etc/systemd/system/golemsp-bot.service`, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable golemsp-bot.service
sudo systemctl start golemsp-bot.service
```

## License

This project is provided as-is for personal use.

