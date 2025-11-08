#!/usr/bin/env python3
"""
Telegram bot for checking GolemSP status.
"""

import os
import subprocess
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
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


def run_golemsp_status():
    """
    Execute 'golemsp status' command and return the output.
    
    Returns:
        tuple: (success: bool, output: str, error: str)
    """
    try:
        result = subprocess.run(
            ['golemsp', 'status'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return True, result.stdout, None
        else:
            return False, None, result.stderr or "Command failed with non-zero exit code"
    
    except FileNotFoundError:
        return False, None, "golemsp command not found. Please ensure GolemSP is installed and in PATH."
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    keyboard = [
        [InlineKeyboardButton("Check GolemSP Status", callback_data='check_status')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = (
        "Welcome to GolemSP Status Bot!\n\n"
        "Click the button below to check the current status of GolemSP."
    )
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callback queries."""
    query = update.callback_query
    
    # Acknowledge the callback query
    await query.answer()
    
    if query.data == 'check_status':
        # Show typing indicator
        await context.bot.send_chat_action(
            chat_id=query.message.chat_id,
            action='typing'
        )
        
        # Run the status command
        success, output, error = run_golemsp_status()
        
        if success:
            formatted_message = format_status_message(output)
            await query.edit_message_text(
                formatted_message,
                parse_mode='Markdown'
            )
        else:
            error_message = f"❌ Error checking GolemSP status:\n\n`{error}`"
            await query.edit_message_text(
                error_message,
                parse_mode='Markdown'
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
            parse_mode='Markdown'
        )
    else:
        error_message = f"❌ Error checking GolemSP status:\n\n`{error}`"
        await update.message.reply_text(
            error_message,
            parse_mode='Markdown'
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
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start the bot
    logger.info("Starting GolemSP Status Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

