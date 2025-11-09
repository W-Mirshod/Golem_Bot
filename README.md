# Multi-Platform Status Telegram Bot

A Telegram bot that allows you to monitor and manage multiple distributed computing platforms including GolemSP, Render Network, and AI training platforms (Together.ai, Akash Network).

## Features

- **Multi-platform support:**
  - 🚀 GolemSP status monitoring
  - 🎨 Render Network status monitoring
  - 🤖 AI Training platforms (Together.ai, Akash Network) monitoring
- Check platform status via inline keyboard buttons
- Direct command support (`/status`, `/render_status`, `/ai_status`, `/all_status`)
- Formatted status output with all service information
- Error handling for service issues
- **Real-time notifications for:**
  - 🎯 New job assignments (all platforms)
  - ✅ Job completions (all platforms)
  - 💰 Payment/earnings updates (all platforms)
- Background monitoring with configurable intervals
- User notification management (enable/disable)
- Unified dashboard showing all platforms at once

## Prerequisites

- Python 3.8 or higher
- GolemSP installed and accessible via `golemsp` command (for GolemSP monitoring)
- A Telegram bot token
- (Optional) Render Network worker installed and running (for Render Network monitoring)
- (Optional) AI training platform workers installed and running (for AI training monitoring)

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

### Platform Configuration

You can enable/disable platforms and configure their settings in your `.env` file:

**Monitoring Configuration:**
- `MONITORING_ENABLED` (default: `true`) - Enable/disable background monitoring
- `MONITORING_INTERVAL` (default: `300`) - Check interval in seconds (300 = 5 minutes)

**Platform Enable/Disable:**
- `RENDER_NETWORK_ENABLED` (default: `false`) - Enable Render Network monitoring
- `AI_TRAINING_ENABLED` (default: `false`) - Enable AI training platform monitoring

**Render Network Configuration (if enabled):**
- `RENDER_API_KEY` (optional) - Render Network API key for advanced features
- `RENDER_NODE_ID` (optional) - Your Render Network node ID

**AI Training Platform Configuration (if enabled):**
- `TOGETHER_AI_ENABLED` (optional) - Enable Together.ai platform
- `TOGETHER_AI_API_KEY` (optional) - Together.ai API key
- `AKASH_NODE_ENABLED` (optional) - Enable Akash Network
- `AKASH_API_ENDPOINT` (optional) - Akash Network API endpoint
- `AKASH_PROVIDER_KEY` (optional) - Akash provider key

Example `.env` configuration:
```bash
# Basic configuration
BOT_TOKEN=your_telegram_bot_token_here
MONITORING_ENABLED=true
MONITORING_INTERVAL=300

# Enable platforms
RENDER_NETWORK_ENABLED=true
AI_TRAINING_ENABLED=true

# Platform-specific configuration (optional)
# RENDER_API_KEY=your_render_api_key
# TOGETHER_AI_API_KEY=your_together_ai_api_key
```

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
2. Send `/start` to begin (automatically enables notifications)
3. Use the keyboard buttons to check platform status:
   - **📊 Service Status** - GolemSP node and service details
   - **💰 Wallet Info** - GolemSP balance and address
   - **⚡ Task Statistics** - GolemSP processing metrics
   - **🎨 Render Status** - Render Network status (if enabled)
   - **🤖 AI Training Status** - AI training platforms status (if enabled)
   - **🌐 All Platforms** - Combined status of all enabled platforms

### Commands

**Status Commands:**
- `/status` - Check full GolemSP status
- `/render_status` - Check Render Network status (if enabled)
- `/ai_status` - Check AI Training platforms status (if enabled)
- `/all_status` - Check all enabled platforms at once

**Notification Commands:**
- `/enable_notifications` - Enable job and payment notifications
- `/disable_notifications` - Disable notifications
- `/notification_status` - Check your current notification settings

### Notification Types

The bot will send you real-time notifications when:

- **🎯 New Job Alert**: When you receive new tasks to process (all platforms)
- **✅ Job Completed**: When tasks are successfully completed (all platforms)
- **💰 Payment/Earnings Update**: When you receive payments or earnings updates (all platforms)

Notifications are sent every 5 minutes (configurable) when changes are detected. Each notification includes the platform name (e.g., "GolemSP: New Job Alert!", "Render Network: Earnings Update!").

## Status Information

**GolemSP:**
- Service status (running/stopped)
- Version, Commit, Date, Build
- Node Name, Subnet, VM status
- Driver status
- Wallet address and balance (on-chain and polygon)
- Task statistics (processed, in progress, etc.)

**Render Network:**
- Worker status (running/stopped)
- Active jobs count
- Completed jobs count
- Total earnings (RENDER tokens)
- Pending earnings

**AI Training Platforms:**
- Worker status (running/stopped)
- Active platforms (Together.ai, Akash Network)
- Active jobs count
- Completed jobs count
- Total earnings
- Pending earnings

## Platform Setup

### Render Network Setup

1. **Install Render Network Worker:**
   - Visit [Render Network](https://render.network) for installation instructions
   - Ensure the Render worker process is running on your system

2. **Enable in Bot:**
   - Set `RENDER_NETWORK_ENABLED=true` in your `.env` file
   - Optionally set `RENDER_API_KEY` if you have API access

3. **Verify:**
   - Use `/render_status` command or click "🎨 Render Status" button
   - Check that worker status shows as "running"

**Note:** Without GPU, Render Network earnings will be significantly lower. CPU-based rendering work is limited.

### AI Training Platform Setup

#### Together.ai Setup

1. **Register and Setup:**
   - Visit [Together.ai](https://together.ai) and create an account
   - Follow their provider setup instructions
   - Install and configure the Together.ai worker

2. **Enable in Bot:**
   - Set `AI_TRAINING_ENABLED=true` in your `.env` file
   - Optionally set `TOGETHER_AI_ENABLED=true` and `TOGETHER_AI_API_KEY` if using Together.ai

#### Akash Network Setup

1. **Register and Setup:**
   - Visit [Akash Network](https://akash.network) and create an account
   - Follow their provider setup instructions
   - Install and configure the Akash provider

2. **Enable in Bot:**
   - Set `AI_TRAINING_ENABLED=true` in your `.env` file
   - Optionally set `AKASH_NODE_ENABLED=true` and `AKASH_API_ENDPOINT` if using Akash

3. **Verify:**
   - Use `/ai_status` command or click "🤖 AI Training Status" button
   - Check that worker status shows as "running"

**Important Notes:**
- **No GPU**: Without a GPU, AI training earnings will be very limited. Most AI training workloads require GPU acceleration.
- **CPU-only workloads**: Some platforms may accept CPU-only workloads, but earnings will be significantly lower than GPU-based work.
- **API Keys**: Some platforms require API keys for full functionality. Check each platform's documentation for API access requirements.

## Troubleshooting

### Bot doesn't respond
- Check that the bot token is correct in `.env` file
- Ensure the bot is running (check console for errors)
- Verify you're messaging the correct bot

### "golemsp command not found" error
- Ensure GolemSP is installed
- Verify `golemsp` is in your PATH
- Try running `golemsp status` manually in terminal
- If using Docker, check that the volume mount path in `docker-compose.yml` is correct

### Permission denied error
- Ensure the `golemsp` binary has execute permissions:
  ```bash
  chmod +x /usr/local/bin/golemsp
  # Or wherever your golemsp binary is located
  ```
- Check file ownership if running in Docker:
  ```bash
  ls -l /usr/local/bin/golemsp
  ```
- If using Docker, the container may need to run as root or with proper user permissions
- Verify the user running the bot has permission to execute the binary

### Command timeout
- The bot has a 30-second timeout for the status command
- If GolemSP is slow to respond, you may need to increase the timeout in `bot.py`

### Render Network not showing status
- Ensure `RENDER_NETWORK_ENABLED=true` is set in `.env`
- Verify that Render Network worker process is running: `pgrep -fl render`
- Check that the worker process is accessible from the bot container
- If using API, verify `RENDER_API_KEY` is correct

### AI Training platforms not showing status
- Ensure `AI_TRAINING_ENABLED=true` is set in `.env`
- Verify that AI training worker process is running: `pgrep -fl together` or `pgrep -fl akash`
- Check that the worker process is accessible from the bot container
- If using API, verify API keys are correct
- **Note**: Without GPU, most AI training platforms will have limited or no work available

### Platform buttons not appearing
- Check that the platform is enabled in `.env` (e.g., `RENDER_NETWORK_ENABLED=true`)
- Restart the bot after changing `.env` configuration
- Verify the bot has loaded the new configuration (check logs)

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

