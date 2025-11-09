#!/usr/bin/env python3
"""
Telegram bot for checking GolemSP status.
"""

import os
import stat
import subprocess
import shutil
import logging
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from platforms.render_network import check_render_status, parse_render_status, format_render_status
from platforms.ai_training import check_ai_training_status, parse_ai_training_status, format_ai_training_status

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set. Please set it in .env file or environment.")

# Configuration for monitoring
MONITORING_ENABLED = os.getenv('MONITORING_ENABLED', 'true').lower() == 'true'
MONITORING_INTERVAL = int(os.getenv('MONITORING_INTERVAL', '300'))  # 5 minutes default
STATE_FILE = os.path.join(os.path.dirname(__file__), 'bot_state.json')
USERS_FILE = os.path.join(os.path.dirname(__file__), 'registered_users.json')

# Platform configuration
RENDER_NETWORK_ENABLED = os.getenv('RENDER_NETWORK_ENABLED', 'false').lower() == 'true'
AI_TRAINING_ENABLED = os.getenv('AI_TRAINING_ENABLED', 'false').lower() == 'true'

# Global variables for monitoring
monitoring_task = None
last_status_data = None
registered_users = set()  # Store chat IDs of users who want notifications


def find_golemsp_binary():
    """
    Find the golemsp binary location.
    
    Returns:
        str or None: Path to golemsp binary, or None if not found
    """
    # Try using shutil.which first
    golemsp_path = shutil.which('golemsp')
    if golemsp_path:
        return golemsp_path
    
    # Try common locations
    common_paths = [
        '/usr/local/bin/golemsp',
        '/usr/bin/golemsp',
        '/opt/golemsp/bin/golemsp',
        os.path.expanduser('~/.local/bin/golemsp'),
    ]
    
    for path in common_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    
    return None


def check_golemsp_permissions(golemsp_path):
    """
    Check if golemsp binary has execute permissions.
    
    Args:
        golemsp_path: Path to golemsp binary
        
    Returns:
        tuple: (has_permission: bool, error_message: str)
    """
    if not golemsp_path:
        return False, "golemsp binary not found"
    
    if not os.path.exists(golemsp_path):
        return False, f"golemsp binary not found at {golemsp_path}"
    
    if not os.access(golemsp_path, os.X_OK):
        # Check file permissions
        file_stat = os.stat(golemsp_path)
        mode = file_stat.st_mode
        
        # Check if it's executable by owner, group, or others
        is_executable = bool(
            mode & stat.S_IXUSR or  # Owner execute
            mode & stat.S_IXGRP or  # Group execute
            mode & stat.S_IXOTH     # Others execute
        )
        
        if not is_executable:
            return False, (
                f"golemsp binary at {golemsp_path} does not have execute permissions. "
                f"Run: chmod +x {golemsp_path}"
            )
        else:
            return False, (
                f"Permission denied executing {golemsp_path}. "
                f"Current user may not have permission. Check file ownership and permissions."
            )
    
    return True, None


def run_golemsp_status():
    """
    Execute 'golemsp status' command and return the output.
    
    Returns:
        tuple: (success: bool, output: str, error: str)
    """
    # Find golemsp binary
    golemsp_path = find_golemsp_binary()
    
    if not golemsp_path:
        return False, None, (
            "golemsp command not found. Please ensure GolemSP is installed and in PATH, "
            "or update the docker-compose.yml volume mount path."
        )
    
    # Check permissions
    has_permission, perm_error = check_golemsp_permissions(golemsp_path)
    if not has_permission:
        return False, None, perm_error
    
    try:
        # Use the full path to golemsp
        result = subprocess.run(
            [golemsp_path, 'status'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return True, result.stdout, None
        else:
            return False, None, result.stderr or "Command failed with non-zero exit code"
    
    except PermissionError as e:
        return False, None, (
            f"Permission denied executing golemsp: {str(e)}\n"
            f"Binary location: {golemsp_path}\n"
            f"Try: chmod +x {golemsp_path} or check file ownership."
        )
    except FileNotFoundError:
        return False, None, f"golemsp binary not found at {golemsp_path}"
    except subprocess.TimeoutExpired:
        return False, None, "Command timed out after 30 seconds."
    except Exception as e:
        return False, None, f"Error executing command: {str(e)}"


def load_previous_state():
    """
    Load the previous bot state from file.

    Returns:
        dict: Previous state data or empty dict if not found
    """
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading state file: {e}")

    return {}


def save_current_state(state_data):
    """
    Save the current bot state to file.

    Args:
        state_data: Dictionary containing current state
    """
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving state file: {e}")


def load_registered_users():
    """
    Load registered users from file.

    Returns:
        set: Set of registered chat IDs
    """
    global registered_users
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                user_list = json.load(f)
                registered_users = set(user_list)
    except Exception as e:
        logger.error(f"Error loading users file: {e}")
        registered_users = set()

    return registered_users


def save_registered_users():
    """
    Save registered users to file.
    """
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(list(registered_users), f, indent=2)
    except Exception as e:
        logger.error(f"Error saving users file: {e}")


def register_user(chat_id):
    """
    Register a user for notifications.

    Args:
        chat_id: Telegram chat ID to register
    """
    registered_users.add(chat_id)
    save_registered_users()
    logger.info(f"User {chat_id} registered for notifications")


def unregister_user(chat_id):
    """
    Unregister a user from notifications.

    Args:
        chat_id: Telegram chat ID to unregister
    """
    registered_users.discard(chat_id)
    save_registered_users()
    logger.info(f"User {chat_id} unregistered from notifications")


def parse_status_data(status_output):
    """
    Parse the golemsp status output and extract detailed information.

    Args:
        status_output: Raw output from golemsp status command

    Returns:
        dict: Parsed status data
    """
    if not status_output:
        return {}

    lines = status_output.strip().split('\n')
    data = {
        'timestamp': datetime.now().isoformat(),
        'service': {},
        'wallet': {},
        'tasks': {}
    }

    current_section = None

    for line in lines:
        cleaned_line = line.replace('│', '').strip()
        if not cleaned_line:
            continue

        # Detect sections
        if 'Status' in cleaned_line and ('─' in line or 'Status' in cleaned_line):
            current_section = 'status'
            continue
        elif 'Wallet' in cleaned_line and ('─' in line or 'Wallet' in cleaned_line):
            current_section = 'wallet'
            continue
        elif 'Tasks' in cleaned_line and ('─' in line or 'Tasks' in cleaned_line):
            current_section = 'tasks'
            continue

        # Skip separator lines
        if any(char in line for char in ['─', '┌', '└', '├', '┤', '┐', '┘']):
            continue

        # Parse status section
        if current_section == 'status':
            if 'Service' in cleaned_line and 'running' in cleaned_line:
                data['service']['status'] = 'running'
            elif 'Version' in cleaned_line and any(char.isdigit() for char in cleaned_line):
                data['service']['version'] = cleaned_line.split('Version')[-1].strip()
            elif 'Node Name' in cleaned_line:
                data['service']['node_name'] = cleaned_line.split('Node Name')[-1].strip()
            elif 'Subnet' in cleaned_line:
                data['service']['subnet'] = cleaned_line.split('Subnet')[-1].strip()

        # Parse wallet section
        elif current_section == 'wallet':
            if cleaned_line.startswith('0x') and len(cleaned_line) > 10:
                data['wallet']['address'] = cleaned_line
            elif 'amount (total)' in cleaned_line:
                # Extract GLM amount from line like "amount (total): 123.456 GLM"
                amount_part = cleaned_line.split('amount (total)')[-1].strip()
                if 'GLM' in amount_part:
                    try:
                        amount = float(amount_part.split()[0])
                        data['wallet']['total_glm'] = amount
                    except (ValueError, IndexError):
                        pass
            elif cleaned_line.startswith('pending') and 'GLM' in cleaned_line:
                try:
                    amount = float(cleaned_line.split()[1])
                    data['wallet']['pending_glm'] = amount
                except (ValueError, IndexError):
                    pass

        # Parse tasks section
        elif current_section == 'tasks':
            if 'last 1h processed' in cleaned_line:
                try:
                    count = int(cleaned_line.split('last 1h processed')[-1].strip())
                    data['tasks']['last_hour_processed'] = count
                except (ValueError, IndexError):
                    pass
            elif 'last 1h in progress' in cleaned_line:
                try:
                    count = int(cleaned_line.split('last 1h in progress')[-1].strip())
                    data['tasks']['in_progress'] = count
                except (ValueError, IndexError):
                    pass
            elif 'total processed' in cleaned_line:
                try:
                    count = int(cleaned_line.split('total processed')[-1].strip())
                    data['tasks']['total_processed'] = count
                except (ValueError, IndexError):
                    pass

    return data


def detect_changes(current_data, previous_data):
    """
    Detect changes between current and previous status data.

    Args:
        current_data: Current parsed status data
        previous_data: Previous parsed status data

    Returns:
        dict: Dictionary containing detected changes
    """
    changes = {
        'new_jobs': False,
        'completed_jobs': False,
        'payment_received': False,
        'wallet_balance_change': 0.0
    }

    if not previous_data:
        return changes

    # Check for new jobs (increase in tasks in progress)
    current_in_progress = current_data.get('tasks', {}).get('in_progress', 0)
    previous_in_progress = previous_data.get('tasks', {}).get('in_progress', 0)
    if current_in_progress > previous_in_progress:
        changes['new_jobs'] = True

    # Check for completed jobs (increase in total processed)
    current_total = current_data.get('tasks', {}).get('total_processed', 0)
    previous_total = previous_data.get('tasks', {}).get('total_processed', 0)
    if current_total > previous_total:
        changes['completed_jobs'] = True

    # Check for payment received (increase in wallet balance)
    current_balance = current_data.get('wallet', {}).get('total_glm', 0.0)
    previous_balance = previous_data.get('wallet', {}).get('total_glm', 0.0)
    balance_change = current_balance - previous_balance
    if balance_change > 0.001:  # Small threshold to avoid floating point issues
        changes['payment_received'] = True
        changes['wallet_balance_change'] = balance_change

    return changes


def format_status_message(status_output):
    """
    Format the golemsp status output beautifully for Telegram.

    Args:
        status_output: Raw output from golemsp status command

    Returns:
        str: Beautifully formatted message for Telegram
    """
    if not status_output:
        return "❌ No status output received."

    # Parse the status output and extract key information
    lines = status_output.strip().split('\n')

    # Initialize data containers
    service_info = {}
    wallet_info = {}
    tasks_info = {}

    current_section = None

    for line in lines:
        # Clean the line by removing box drawing characters and extra whitespace
        cleaned_line = line.replace('│', '').strip()
        if not cleaned_line:
            continue

        # Detect sections
        if 'Status' in cleaned_line and ('─' in line or 'Status' in cleaned_line):
            current_section = 'status'
            continue
        elif 'Wallet' in cleaned_line and ('─' in line or 'Wallet' in cleaned_line):
            current_section = 'wallet'
            continue
        elif 'Tasks' in cleaned_line and ('─' in line or 'Tasks' in cleaned_line):
            current_section = 'tasks'
            continue

        # Skip separator lines and box drawing
        if any(char in line for char in ['─', '┌', '└', '├', '┤', '┐', '┘']):
            continue

        # Parse status section
        if current_section == 'status':
            if 'Service' in cleaned_line and 'running' in cleaned_line:
                service_info['status'] = '🟢 Running'
            elif 'Version' in cleaned_line and any(char.isdigit() for char in cleaned_line):
                service_info['version'] = cleaned_line.split('Version')[-1].strip()
            elif 'Node Name' in cleaned_line:
                service_info['node_name'] = cleaned_line.split('Node Name')[-1].strip()
            elif 'Subnet' in cleaned_line:
                service_info['subnet'] = cleaned_line.split('Subnet')[-1].strip()
            elif 'VM' in cleaned_line and 'invalid environment' in cleaned_line:
                service_info['vm'] = '🔴 Invalid Environment (Docker)'

        # Parse wallet section
        elif current_section == 'wallet':
            if cleaned_line.startswith('0x') and len(cleaned_line) > 10:
                wallet_info['address'] = f"`{cleaned_line}`"
            elif 'network' in cleaned_line and 'mainnet' in cleaned_line:
                wallet_info['network'] = '🌐 Mainnet'
            elif 'amount (total)' in cleaned_line:
                wallet_info['total'] = cleaned_line.split('amount (total)')[-1].strip()
            elif cleaned_line.startswith('pending') and 'GLM' in cleaned_line:
                wallet_info['pending'] = cleaned_line.split('pending')[-1].strip()

        # Parse tasks section
        elif current_section == 'tasks':
            if 'last 1h processed' in cleaned_line:
                tasks_info['last_hour'] = cleaned_line.split('last 1h processed')[-1].strip()
            elif 'last 1h in progress' in cleaned_line:
                tasks_info['in_progress'] = cleaned_line.split('last 1h in progress')[-1].strip()
            elif 'total processed' in cleaned_line:
                tasks_info['total'] = cleaned_line.split('total processed')[-1].strip()

    # Build beautiful formatted message
    message_parts = []

    # Header
    message_parts.append("🚀 *GolemSP Status Dashboard*\n")

    # Service Status Section
    if service_info:
        message_parts.append("📊 *Service Information*")
        message_parts.append(f"• Status: {service_info.get('status', 'Unknown')}")
        if 'version' in service_info:
            message_parts.append(f"• Version: `{service_info['version']}`")
        if 'node_name' in service_info:
            message_parts.append(f"• Node: `{service_info['node_name']}`")
        if 'subnet' in service_info:
            message_parts.append(f"• Subnet: `{service_info['subnet']}`")
        if 'vm' in service_info:
            message_parts.append(f"• VM Status: {service_info['vm']}")
        message_parts.append("")

    # Wallet Section
    if wallet_info:
        message_parts.append("💰 *Wallet Information*")
        if 'address' in wallet_info:
            message_parts.append(f"• Address: {wallet_info['address']}")
        if 'network' in wallet_info:
            message_parts.append(f"• Network: {wallet_info['network']}")
        if 'total' in wallet_info:
            message_parts.append(f"• Balance: `{wallet_info['total']}`")
        if 'pending' in wallet_info:
            message_parts.append(f"• Pending: `{wallet_info['pending']}`")
        message_parts.append("")

    # Tasks Section
    if tasks_info:
        message_parts.append("⚡ *Task Statistics*")
        if 'last_hour' in tasks_info:
            message_parts.append(f"• Last Hour Processed: `{tasks_info['last_hour']}`")
        if 'in_progress' in tasks_info:
            message_parts.append(f"• Currently In Progress: `{tasks_info['in_progress']}`")
        if 'total' in tasks_info:
            message_parts.append(f"• Total Processed: `{tasks_info['total']}`")

    # Footer with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    message_parts.append(f"\n🕒 Last updated: `{timestamp}`")

    return '\n'.join(message_parts)


def format_status_section(status_output):
    """Format only the status section beautifully."""
    if not status_output:
        return "❌ No status output received."

    service_info = {}

    lines = status_output.strip().split('\n')
    current_section = None

    for line in lines:
        cleaned_line = line.replace('│', '').strip()
        if not cleaned_line:
            continue

        if 'Status' in cleaned_line and ('─' in line or 'Status' in cleaned_line):
            current_section = 'status'
            continue

        if any(char in line for char in ['─', '┌', '└', '├', '┤', '┐', '┘']):
            continue

        if current_section == 'status':
            if 'Service' in cleaned_line and 'running' in cleaned_line:
                service_info['status'] = '🟢 Running'
            elif 'Version' in cleaned_line and any(char.isdigit() for char in cleaned_line):
                service_info['version'] = cleaned_line.split('Version')[-1].strip()
            elif 'Node Name' in cleaned_line:
                service_info['node_name'] = cleaned_line.split('Node Name')[-1].strip()
            elif 'Subnet' in cleaned_line:
                service_info['subnet'] = cleaned_line.split('Subnet')[-1].strip()
            elif 'VM' in cleaned_line and 'invalid environment' in cleaned_line:
                service_info['vm'] = '🔴 Invalid Environment (Docker)'

    message_parts = ["📊 *Service Information*"]
    message_parts.append(f"• Status: {service_info.get('status', 'Unknown')}")
    if 'version' in service_info:
        message_parts.append(f"• Version: `{service_info['version']}`")
    if 'node_name' in service_info:
        message_parts.append(f"• Node: `{service_info['node_name']}`")
    if 'subnet' in service_info:
        message_parts.append(f"• Subnet: `{service_info['subnet']}`")
    if 'vm' in service_info:
        message_parts.append(f"• VM Status: {service_info['vm']}")

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    message_parts.append(f"\n🕒 Last updated: `{timestamp}`")

    return '\n'.join(message_parts)


def format_wallet_section(status_output):
    """Format only the wallet section beautifully."""
    if not status_output:
        return "❌ No status output received."

    wallet_info = {}

    lines = status_output.strip().split('\n')
    current_section = None

    for line in lines:
        cleaned_line = line.replace('│', '').strip()
        if not cleaned_line:
            continue

        if 'Wallet' in cleaned_line and ('─' in line or 'Wallet' in cleaned_line):
            current_section = 'wallet'
            continue

        if any(char in line for char in ['─', '┌', '└', '├', '┤', '┐', '┘']):
            continue

        if current_section == 'wallet':
            if cleaned_line.startswith('0x') and len(cleaned_line) > 10:
                wallet_info['address'] = f"`{cleaned_line}`"
            elif 'network' in cleaned_line and 'mainnet' in cleaned_line:
                wallet_info['network'] = '🌐 Mainnet'
            elif 'amount (total)' in cleaned_line:
                wallet_info['total'] = cleaned_line.split('amount (total)')[-1].strip()
            elif cleaned_line.startswith('pending') and 'GLM' in cleaned_line:
                wallet_info['pending'] = cleaned_line.split('pending')[-1].strip()

    message_parts = ["💰 *Wallet Information*"]
    if 'address' in wallet_info:
        message_parts.append(f"• Address: {wallet_info['address']}")
    if 'network' in wallet_info:
        message_parts.append(f"• Network: {wallet_info['network']}")
    if 'total' in wallet_info:
        message_parts.append(f"• Balance: `{wallet_info['total']}`")
    if 'pending' in wallet_info:
        message_parts.append(f"• Pending: `{wallet_info['pending']}`")

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    message_parts.append(f"\n🕒 Last updated: `{timestamp}`")

    return '\n'.join(message_parts)


def format_tasks_section(status_output):
    """Format only the tasks section beautifully."""
    if not status_output:
        return "❌ No status output received."

    tasks_info = {}

    lines = status_output.strip().split('\n')
    current_section = None

    for line in lines:
        cleaned_line = line.replace('│', '').strip()
        if not cleaned_line:
            continue

        if 'Tasks' in cleaned_line and ('─' in line or 'Tasks' in cleaned_line):
            current_section = 'tasks'
            continue

        if any(char in line for char in ['─', '┌', '└', '├', '┤', '┐', '┘']):
            continue

        if current_section == 'tasks':
            if 'last 1h processed' in cleaned_line:
                tasks_info['last_hour'] = cleaned_line.split('last 1h processed')[-1].strip()
            elif 'last 1h in progress' in cleaned_line:
                tasks_info['in_progress'] = cleaned_line.split('last 1h in progress')[-1].strip()
            elif 'total processed' in cleaned_line:
                tasks_info['total'] = cleaned_line.split('total processed')[-1].strip()

    message_parts = ["⚡ *Task Statistics*"]
    if 'last_hour' in tasks_info:
        message_parts.append(f"• Last Hour Processed: `{tasks_info['last_hour']}`")
    if 'in_progress' in tasks_info:
        message_parts.append(f"• Currently In Progress: `{tasks_info['in_progress']}`")
    if 'total' in tasks_info:
        message_parts.append(f"• Total Processed: `{tasks_info['total']}`")

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    message_parts.append(f"\n🕒 Last updated: `{timestamp}`")

    return '\n'.join(message_parts)


async def enable_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enable notifications for the current user."""
    chat_id = update.message.chat_id
    register_user(chat_id)

    await update.message.reply_text(
        "✅ *Notifications Enabled!*\n\n"
        "You'll now receive notifications when:\n"
        "• You get new jobs\n"
        "• Jobs are completed\n"
        "• You receive payments (GLM)\n\n"
        "Use /disable_notifications to stop receiving alerts.",
        parse_mode='Markdown',
        reply_markup=get_reply_keyboard()
    )


async def disable_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disable notifications for the current user."""
    chat_id = update.message.chat_id
    unregister_user(chat_id)

    await update.message.reply_text(
        "🔕 *Notifications Disabled*\n\n"
        "You won't receive job and payment notifications anymore.\n\n"
        "Use /enable_notifications to start receiving alerts again.",
        parse_mode='Markdown',
        reply_markup=get_reply_keyboard()
    )


async def notification_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check notification status for the current user."""
    chat_id = update.message.chat_id
    is_registered = chat_id in registered_users

    status_text = "🔔 *Notifications: ENABLED*" if is_registered else "🔕 *Notifications: DISABLED*"

    if is_registered:
        status_text += "\n\nYou're receiving notifications for jobs and payments."
    else:
        status_text += "\n\nUse /enable_notifications to start receiving alerts."

    await update.message.reply_text(
        status_text,
        parse_mode='Markdown',
        reply_markup=get_reply_keyboard()
    )


def get_reply_keyboard():
    """Create the persistent reply keyboard."""
    keyboard = [
        [KeyboardButton("📊 Service Status"), KeyboardButton("💰 Wallet Info")],
        [KeyboardButton("⚡ Task Statistics")]
    ]
    
    # Always show platform buttons, even if not enabled
    platform_row = []
    platform_row.append(KeyboardButton("🎨 Render Status"))
    platform_row.append(KeyboardButton("🤖 AI Training Status"))
    keyboard.append(platform_row)
    keyboard.append([KeyboardButton("🌐 All Platforms")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


async def send_notification(bot, chat_id, message):
    """
    Send a notification message to the user.

    Args:
        bot: Telegram bot instance
        chat_id: Chat ID to send notification to
        message: Notification message
    """
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown'
        )
        logger.info(f"Notification sent: {message[:50]}...")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")


async def monitoring_loop(application):
    """
    Background monitoring loop that checks for job and payment changes across all platforms.
    """
    global last_status_data

    logger.info(f"Starting monitoring loop with {MONITORING_INTERVAL}s interval")

    # Load previous state
    previous_state = load_previous_state()
    previous_render_state = previous_state.get('render', {})
    previous_ai_state = previous_state.get('ai_training', {})

    while True:
        try:
            # Check if monitoring is still enabled
            if not MONITORING_ENABLED:
                logger.info("Monitoring disabled, stopping loop")
                break

            notification_messages = []

            # Check GolemSP status
            success, output, error = run_golemsp_status()
            if success:
                current_data = parse_status_data(output)
                golem_previous = previous_state.get('golem', {})

                # Detect changes
                changes = detect_changes(current_data, golem_previous)

                if any(changes.values()) and registered_users:
                    if changes['new_jobs']:
                        current_jobs = current_data.get('tasks', {}).get('in_progress', 0)
                        previous_jobs = golem_previous.get('tasks', {}).get('in_progress', 0)
                        new_jobs_count = current_jobs - previous_jobs
                        notification_messages.append(
                            f"🎯 *GolemSP: New Job Alert!*\n"
                            f"You've received {new_jobs_count} new task(s)!\n"
                            f"Currently processing: {current_jobs} tasks"
                        )

                    if changes['completed_jobs']:
                        current_total = current_data.get('tasks', {}).get('total_processed', 0)
                        previous_total = golem_previous.get('tasks', {}).get('total_processed', 0)
                        completed_count = current_total - previous_total
                        notification_messages.append(
                            f"✅ *GolemSP: Job Completed!*\n"
                            f"Successfully completed {completed_count} task(s)!\n"
                            f"Total processed: {current_total} tasks"
                        )

                    if changes['payment_received']:
                        balance_change = changes['wallet_balance_change']
                        current_balance = current_data.get('wallet', {}).get('total_glm', 0.0)
                        notification_messages.append(
                            f"💰 *GolemSP: Payment Received!*\n"
                            f"You've received `{balance_change:.6f} GLM`!\n"
                            f"Current balance: `{current_balance:.6f} GLM`"
                        )

                # Update previous state
                previous_state['golem'] = current_data.copy()
            else:
                logger.warning(f"Failed to get GolemSP status in monitoring loop: {error}")

            # Check Render Network status
            if RENDER_NETWORK_ENABLED:
                success, data, error = check_render_status()
                if success:
                    current_render_data = parse_render_status(data)
                    
                    # Check for changes
                    prev_earnings = previous_render_state.get('total_earnings', 0.0)
                    curr_earnings = current_render_data.get('total_earnings', 0.0)
                    prev_jobs = previous_render_state.get('active_jobs', 0)
                    curr_jobs = current_render_data.get('active_jobs', 0)
                    
                    if curr_earnings > prev_earnings and registered_users:
                        earnings_change = curr_earnings - prev_earnings
                        notification_messages.append(
                            f"💰 *Render Network: Earnings Update!*\n"
                            f"You've earned `{earnings_change:.6f} RENDER`!\n"
                            f"Total earnings: `{curr_earnings:.6f} RENDER`"
                        )
                    
                    if curr_jobs > prev_jobs and registered_users:
                        new_jobs = curr_jobs - prev_jobs
                        notification_messages.append(
                            f"🎯 *Render Network: New Job!*\n"
                            f"You've received {new_jobs} new job(s)!\n"
                            f"Active jobs: {curr_jobs}"
                        )
                    
                    previous_render_state = current_render_data.copy()
                else:
                    logger.warning(f"Failed to get Render Network status: {error}")

            # Check AI Training status
            if AI_TRAINING_ENABLED:
                success, data, error = check_ai_training_status()
                if success:
                    current_ai_data = parse_ai_training_status(data)
                    
                    # Check for changes
                    prev_earnings = previous_ai_state.get('total_earnings', 0.0)
                    curr_earnings = current_ai_data.get('total_earnings', 0.0)
                    prev_jobs = previous_ai_state.get('active_jobs', 0)
                    curr_jobs = current_ai_data.get('active_jobs', 0)
                    
                    if curr_earnings > prev_earnings and registered_users:
                        earnings_change = curr_earnings - prev_earnings
                        notification_messages.append(
                            f"💰 *AI Training: Earnings Update!*\n"
                            f"You've earned `{earnings_change:.6f}`!\n"
                            f"Total earnings: `{curr_earnings:.6f}`"
                        )
                    
                    if curr_jobs > prev_jobs and registered_users:
                        new_jobs = curr_jobs - prev_jobs
                        notification_messages.append(
                            f"🎯 *AI Training: New Job!*\n"
                            f"You've received {new_jobs} new job(s)!\n"
                            f"Active jobs: {curr_jobs}"
                        )
                    
                    previous_ai_state = current_ai_data.copy()
                else:
                    logger.warning(f"Failed to get AI Training status: {error}")

            # Send notifications to all registered users
            if notification_messages and registered_users:
                for chat_id in registered_users.copy():
                    for message in notification_messages:
                        await send_notification(application.bot, chat_id, message)
                        await asyncio.sleep(0.1)  # Small delay to avoid rate limiting

            # Save current state for next comparison
            previous_state['render'] = previous_render_state
            previous_state['ai_training'] = previous_ai_state
            save_current_state(previous_state)

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")

        # Wait for next check
        await asyncio.sleep(MONITORING_INTERVAL)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    chat_id = update.message.chat_id

    # Automatically register user for notifications
    register_user(chat_id)

    welcome_message = (
        "🎉 *Welcome to Multi-Platform Status Bot!*\n\n"
        "✅ Notifications are now *ENABLED* for you!\n\n"
        "You'll receive alerts when:\n"
        "• 🎯 You get new jobs\n"
        "• ✅ Jobs are completed\n"
        "• 💰 You receive payments\n\n"
        "Use the buttons below to check specific information:\n"
        "📊 Service Status - GolemSP node and service details\n"
        "💰 Wallet Info - GolemSP balance and address\n"
        "⚡ Task Statistics - GolemSP processing metrics\n"
    )
    
    welcome_message += (
        "🎨 Render Status - Render Network status\n"
        "🤖 AI Training Status - AI training platforms status\n"
        "🌐 All Platforms - Combined status of all platforms\n\n"
        "Or use these commands:\n"
        "/status - Check full GolemSP status\n"
        "/render_status - Check Render Network status\n"
        "/ai_status - Check AI Training status\n"
        "/all_status - Check all platforms status\n"
        "/enable_notifications - Enable notifications\n"
        "/disable_notifications - Disable notifications\n"
        "/notification_status - Check notification settings"
    )

    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown',
        reply_markup=get_reply_keyboard()
    )


async def handle_keyboard_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle keyboard button presses."""
    text = update.message.text

    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.message.chat_id,
        action='typing'
    )

    # Handle GolemSP buttons
    if text in ["📊 Service Status", "💰 Wallet Info", "⚡ Task Statistics"]:
        success, output, error = run_golemsp_status()
        if success:
            if text == "📊 Service Status":
                formatted_message = format_status_section(output)
            elif text == "💰 Wallet Info":
                formatted_message = format_wallet_section(output)
            elif text == "⚡ Task Statistics":
                formatted_message = format_tasks_section(output)
        else:
            formatted_message = f"❌ Error checking GolemSP status:\n\n`{error}`"
    
    # Handle Render Network button
    elif text == "🎨 Render Status":
        if not RENDER_NETWORK_ENABLED:
            formatted_message = (
                "🎨 *Render Network Status*\n\n"
                "⚠️ Render Network monitoring is not enabled.\n\n"
                "To enable:\n"
                "1. Set `RENDER_NETWORK_ENABLED=true` in your `.env` file\n"
                "2. Restart the bot\n"
                "3. Ensure Render Network worker is installed and running\n\n"
                "Note: Without GPU, Render Network earnings will be limited."
            )
        else:
            success, data, error = check_render_status()
            if success:
                parsed_data = parse_render_status(data)
                formatted_message = format_render_status(parsed_data)
            else:
                formatted_message = f"❌ Error checking Render Network status:\n\n`{error}`"
    
    # Handle AI Training button
    elif text == "🤖 AI Training Status":
        if not AI_TRAINING_ENABLED:
            formatted_message = (
                "🤖 *AI Training Platform Status*\n\n"
                "⚠️ AI Training platform monitoring is not enabled.\n\n"
                "To enable:\n"
                "1. Set `AI_TRAINING_ENABLED=true` in your `.env` file\n"
                "2. Restart the bot\n"
                "3. Install and configure AI training platform workers:\n"
                "   - Together.ai: https://together.ai\n"
                "   - Akash Network: https://akash.network\n\n"
                "⚠️ Important: Without GPU, AI training earnings will be very limited.\n"
                "Most AI workloads require GPU acceleration."
            )
        else:
            success, data, error = check_ai_training_status()
            if success:
                parsed_data = parse_ai_training_status(data)
                formatted_message = format_ai_training_status(parsed_data)
            else:
                formatted_message = f"❌ Error checking AI Training status:\n\n`{error}`"
    
    # Handle All Platforms button
    elif text == "🌐 All Platforms":
        formatted_message = "🌐 *All Platforms Status*\n\n"
        
        # GolemSP status
        success, output, error = run_golemsp_status()
        if success:
            golem_data = parse_status_data(output)
            golem_balance = golem_data.get('wallet', {}).get('total_glm', 0.0)
            golem_tasks = golem_data.get('tasks', {}).get('in_progress', 0)
            formatted_message += f"🚀 *GolemSP*\n"
            formatted_message += f"• Balance: `{golem_balance:.6f} GLM`\n"
            formatted_message += f"• Active Tasks: `{golem_tasks}`\n\n"
        else:
            formatted_message += f"🚀 *GolemSP*: ❌ Error\n\n"
        
        # Render Network status
        if RENDER_NETWORK_ENABLED:
            success, data, error = check_render_status()
            if success:
                render_data = parse_render_status(data)
                render_earnings = render_data.get('total_earnings', 0.0)
                render_jobs = render_data.get('active_jobs', 0)
                formatted_message += f"🎨 *Render Network*\n"
                formatted_message += f"• Earnings: `{render_earnings:.6f} RENDER`\n"
                formatted_message += f"• Active Jobs: `{render_jobs}`\n\n"
            else:
                formatted_message += f"🎨 *Render Network*: ❌ Error\n\n"
        else:
            formatted_message += f"🎨 *Render Network*: ⚠️ Not enabled\n\n"
        
        # AI Training status
        if AI_TRAINING_ENABLED:
            success, data, error = check_ai_training_status()
            if success:
                ai_data = parse_ai_training_status(data)
                ai_earnings = ai_data.get('total_earnings', 0.0)
                ai_jobs = ai_data.get('active_jobs', 0)
                formatted_message += f"🤖 *AI Training*\n"
                formatted_message += f"• Earnings: `{ai_earnings:.6f}`\n"
                formatted_message += f"• Active Jobs: `{ai_jobs}`\n\n"
            else:
                formatted_message += f"🤖 *AI Training*: ❌ Error\n\n"
        else:
            formatted_message += f"🤖 *AI Training*: ⚠️ Not enabled\n\n"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        formatted_message += f"🕒 Last updated: `{timestamp}`"
    
    else:
        # Unknown button, show help
        formatted_message = "Please use the buttons below to check platform information."

    await update.message.reply_text(
        formatted_message,
        parse_mode='Markdown',
        reply_markup=get_reply_keyboard()
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command directly."""
    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.message.chat_id,
        action='typing'
    )
    
    # Run the status command
    success, output, error = run_golemsp_status()
    
    if success:
        formatted_message = format_status_message(output)
        await update.message.reply_text(
            formatted_message,
            parse_mode='Markdown',
            reply_markup=get_reply_keyboard()
        )
    else:
        error_message = f"❌ Error checking GolemSP status:\n\n`{error}`"
        await update.message.reply_text(
            error_message,
            parse_mode='Markdown',
            reply_markup=get_reply_keyboard()
        )


async def render_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /render_status command."""
    if not RENDER_NETWORK_ENABLED:
        await update.message.reply_text(
            "❌ Render Network is not enabled. Set RENDER_NETWORK_ENABLED=true in .env",
            parse_mode='Markdown',
            reply_markup=get_reply_keyboard()
        )
        return
    
    await context.bot.send_chat_action(
        chat_id=update.message.chat_id,
        action='typing'
    )
    
    success, data, error = check_render_status()
    if success:
        parsed_data = parse_render_status(data)
        formatted_message = format_render_status(parsed_data)
    else:
        formatted_message = f"❌ Error checking Render Network status:\n\n`{error}`"
    
    await update.message.reply_text(
        formatted_message,
        parse_mode='Markdown',
        reply_markup=get_reply_keyboard()
    )


async def ai_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ai_status command."""
    if not AI_TRAINING_ENABLED:
        await update.message.reply_text(
            "❌ AI Training platforms are not enabled. Set AI_TRAINING_ENABLED=true in .env",
            parse_mode='Markdown',
            reply_markup=get_reply_keyboard()
        )
        return
    
    await context.bot.send_chat_action(
        chat_id=update.message.chat_id,
        action='typing'
    )
    
    success, data, error = check_ai_training_status()
    if success:
        parsed_data = parse_ai_training_status(data)
        formatted_message = format_ai_training_status(parsed_data)
    else:
        formatted_message = f"❌ Error checking AI Training status:\n\n`{error}`"
    
    await update.message.reply_text(
        formatted_message,
        parse_mode='Markdown',
        reply_markup=get_reply_keyboard()
    )


async def all_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /all_status command."""
    await context.bot.send_chat_action(
        chat_id=update.message.chat_id,
        action='typing'
    )
    
    formatted_message = "🌐 *All Platforms Status*\n\n"
    
    # GolemSP status
    success, output, error = run_golemsp_status()
    if success:
        golem_data = parse_status_data(output)
        golem_balance = golem_data.get('wallet', {}).get('total_glm', 0.0)
        golem_tasks = golem_data.get('tasks', {}).get('in_progress', 0)
        formatted_message += f"🚀 *GolemSP*\n"
        formatted_message += f"• Balance: `{golem_balance:.6f} GLM`\n"
        formatted_message += f"• Active Tasks: `{golem_tasks}`\n\n"
    else:
        formatted_message += f"🚀 *GolemSP*: ❌ Error\n\n"
    
    # Render Network status
    if RENDER_NETWORK_ENABLED:
        success, data, error = check_render_status()
        if success:
            render_data = parse_render_status(data)
            render_earnings = render_data.get('total_earnings', 0.0)
            render_jobs = render_data.get('active_jobs', 0)
            formatted_message += f"🎨 *Render Network*\n"
            formatted_message += f"• Earnings: `{render_earnings:.6f} RENDER`\n"
            formatted_message += f"• Active Jobs: `{render_jobs}`\n\n"
        else:
            formatted_message += f"🎨 *Render Network*: ❌ Error\n\n"
    else:
        formatted_message += f"🎨 *Render Network*: ⚠️ Not enabled\n\n"
    
    # AI Training status
    if AI_TRAINING_ENABLED:
        success, data, error = check_ai_training_status()
        if success:
            ai_data = parse_ai_training_status(data)
            ai_earnings = ai_data.get('total_earnings', 0.0)
            ai_jobs = ai_data.get('active_jobs', 0)
            formatted_message += f"🤖 *AI Training*\n"
            formatted_message += f"• Earnings: `{ai_earnings:.6f}`\n"
            formatted_message += f"• Active Jobs: `{ai_jobs}`\n\n"
        else:
            formatted_message += f"🤖 *AI Training*: ❌ Error\n\n"
    else:
        formatted_message += f"🤖 *AI Training*: ⚠️ Not enabled\n\n"
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    formatted_message += f"🕒 Last updated: `{timestamp}`"
    
    await update.message.reply_text(
        formatted_message,
        parse_mode='Markdown',
        reply_markup=get_reply_keyboard()
    )


async def start_monitoring(application):
    """Start the background monitoring task."""
    global monitoring_task

    if MONITORING_ENABLED:
        monitoring_task = asyncio.create_task(monitoring_loop(application))
        logger.info("Background monitoring started")
    else:
        logger.info("Monitoring disabled via configuration")


def main():
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Please set it in .env file or environment variables.")
        return

    # Load registered users
    load_registered_users()
    logger.info(f"Loaded {len(registered_users)} registered users")

    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("render_status", render_status_command))
    application.add_handler(CommandHandler("ai_status", ai_status_command))
    application.add_handler(CommandHandler("all_status", all_status_command))
    application.add_handler(CommandHandler("enable_notifications", enable_notifications))
    application.add_handler(CommandHandler("disable_notifications", disable_notifications))
    application.add_handler(CommandHandler("notification_status", notification_status))
    # Handle keyboard button presses and other text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard_button))

    # Start the bot
    logger.info("Starting GolemSP Status Bot...")
    import asyncio

    # Check if there's already an event loop running
    try:
        loop = asyncio.get_running_loop()
        # If we're here, there's already a running loop
        logger.info("Detected running event loop, using alternative startup method")
        # For now, let's try a simpler approach
        import nest_asyncio
        nest_asyncio.apply()
        asyncio.run(application.run_polling())
    except RuntimeError:
        # No running loop, we can use asyncio.run()
        asyncio.run(application.run_polling())


if __name__ == '__main__':
    main()

