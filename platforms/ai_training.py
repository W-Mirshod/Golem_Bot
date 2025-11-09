"""
AI Training platforms (Together.ai, Akash Network) status checking and monitoring.
"""

import os
import subprocess
import logging
import json
from datetime import datetime
from typing import Tuple, Dict, Optional

logger = logging.getLogger(__name__)


def find_ai_training_process() -> Optional[str]:
    """
    Find AI training worker process.
    
    Returns:
        str or None: Process name or path if found
    """
    search_terms = ['together', 'akash', 'ai-training', 'inference']
    
    for term in search_terms:
        try:
            result = subprocess.run(
                ['pgrep', '-fl', term],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split('\n')[0]
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"Error finding AI training process with term '{term}': {e}")
    
    return None


def check_ai_training_worker_running() -> bool:
    """
    Check if AI training worker process is running.
    
    Returns:
        bool: True if worker is running
    """
    process = find_ai_training_process()
    return process is not None


def check_ai_training_status() -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Check AI training platform status (Together.ai, Akash Network).
    
    Returns:
        tuple: (success: bool, data: dict or None, error: str or None)
    """
    try:
        is_running = check_ai_training_worker_running()
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'worker': {
                'status': 'running' if is_running else 'stopped',
                'process': find_ai_training_process()
            },
            'platforms': {
                'together_ai': {
                    'enabled': os.getenv('TOGETHER_AI_ENABLED', 'false').lower() == 'true',
                    'status': 'running' if is_running else 'stopped'
                },
                'akash': {
                    'enabled': os.getenv('AKASH_NODE_ENABLED', 'false').lower() == 'true',
                    'status': 'running' if is_running else 'stopped'
                }
            },
            'jobs': {
                'active': 0,
                'completed': 0
            },
            'earnings': {
                'total': 0.0,
                'pending': 0.0
            }
        }
        
        if not is_running:
            return True, data, "AI training worker is not running"
        
        return True, data, None
        
    except Exception as e:
        logger.error(f"Error checking AI training status: {e}")
        return False, None, f"Error checking AI training status: {str(e)}"


def parse_ai_training_status(data: Dict) -> Dict:
    """
    Parse AI training platform status data for display.
    
    Args:
        data: Raw status data dictionary
        
    Returns:
        dict: Parsed status data
    """
    if not data:
        return {}
    
    platforms = data.get('platforms', {})
    together_enabled = platforms.get('together_ai', {}).get('enabled', False)
    akash_enabled = platforms.get('akash', {}).get('enabled', False)
    
    active_platforms = []
    if together_enabled:
        active_platforms.append('Together.ai')
    if akash_enabled:
        active_platforms.append('Akash Network')
    
    parsed = {
        'worker_status': data.get('worker', {}).get('status', 'unknown'),
        'is_running': data.get('worker', {}).get('status') == 'running',
        'active_platforms': active_platforms,
        'together_ai_enabled': together_enabled,
        'akash_enabled': akash_enabled,
        'active_jobs': data.get('jobs', {}).get('active', 0),
        'completed_jobs': data.get('jobs', {}).get('completed', 0),
        'total_earnings': data.get('earnings', {}).get('total', 0.0),
        'pending_earnings': data.get('earnings', {}).get('pending', 0.0),
        'timestamp': data.get('timestamp', datetime.now().isoformat())
    }
    
    return parsed


def format_ai_training_status(data: Dict) -> str:
    """
    Format AI training platform status for Telegram display.
    
    Args:
        data: Parsed status data
        
    Returns:
        str: Formatted status message
    """
    if not data:
        return "❌ No AI training platform status available."
    
    message_parts = []
    message_parts.append("🤖 *AI Training Platform Status*\n")
    
    worker_status = data.get('worker_status', 'unknown')
    status_emoji = "🟢" if data.get('is_running', False) else "🔴"
    message_parts.append(f"• Worker Status: {status_emoji} {worker_status.capitalize()}")
    
    active_platforms = data.get('active_platforms', [])
    if active_platforms:
        platforms_str = ', '.join(active_platforms)
        message_parts.append(f"• Active Platforms: `{platforms_str}`")
    else:
        message_parts.append("• Active Platforms: `None configured`")
    
    together_enabled = data.get('together_ai_enabled', False)
    akash_enabled = data.get('akash_enabled', False)
    if together_enabled:
        message_parts.append(f"• Together.ai: {'🟢 Enabled' if data.get('is_running') else '🔴 Disabled'}")
    if akash_enabled:
        message_parts.append(f"• Akash Network: {'🟢 Enabled' if data.get('is_running') else '🔴 Disabled'}")
    
    active_jobs = data.get('active_jobs', 0)
    completed_jobs = data.get('completed_jobs', 0)
    message_parts.append(f"• Active Jobs: `{active_jobs}`")
    message_parts.append(f"• Completed Jobs: `{completed_jobs}`")
    
    total_earnings = data.get('total_earnings', 0.0)
    pending_earnings = data.get('pending_earnings', 0.0)
    message_parts.append(f"• Total Earnings: `{total_earnings:.6f}`")
    if pending_earnings > 0:
        message_parts.append(f"• Pending Earnings: `{pending_earnings:.6f}`")
    
    timestamp = data.get('timestamp', datetime.now().isoformat())
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        formatted_time = timestamp
    message_parts.append(f"\n🕒 Last updated: `{formatted_time}`")
    
    return '\n'.join(message_parts)

