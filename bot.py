#!/usr/bin/env python3
"""
Telegram bot for checking GolemSP status.
"""

import os
import stat
import subprocess
import shutil
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

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


def format_status_message(status_output):
    """
    Format the golemsp status output for Telegram.
    
    Args:
        status_output: Raw output from golemsp status command
        
    Returns:
        str: Formatted message for Telegram
    """
    if not status_output:
        return "No status output received."
    
    # Clean up the output and format for Telegram
    lines = status_output.strip().split('\n')
    
    # Format as monospace code block for better readability
    formatted_lines = []
    for line in lines:
        # Remove excessive whitespace but preserve structure
        formatted_lines.append(line.rstrip())
    
    formatted_text = '\n'.join(formatted_lines)
    
    # Wrap in code block for monospace font
    return f"```\n{formatted_text}\n```"


def get_reply_keyboard():
    """Create the persistent reply keyboard."""
    keyboard = [
        [KeyboardButton("Check GolemSP Status")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "Welcome to GolemSP Status Bot!\n\n"
        "Use the button below to check the current status of GolemSP, "
        "or send /status command."
    )
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=get_reply_keyboard()
    )


async def handle_keyboard_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle keyboard button presses."""
    text = update.message.text
    
    if text == "Check GolemSP Status":
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
    else:
        # Unknown message, show keyboard
        await update.message.reply_text(
            "Please use the button below or send /status to check GolemSP status.",
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


def main():
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Please set it in .env file or environment variables.")
        return
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_command))
    # Handle keyboard button presses and other text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard_button))
    
    # Start the bot
    logger.info("Starting GolemSP Status Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

