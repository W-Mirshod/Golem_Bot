"""
Render Network status checking and monitoring.
"""

import os
import subprocess
import logging
import json
from datetime import datetime
from typing import Tuple, Dict, Optional

logger = logging.getLogger(__name__)


def find_render_worker_process() -> Optional[str]:
    """
    Find Render Network worker process.
    
    Returns:
        str or None: Process name or path if found
    """
    try:
        result = subprocess.run(
            ['pgrep', '-fl', 'render'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.debug(f"Error finding render process: {e}")
    
    return None


def check_render_worker_running() -> bool:
    """
    Check if Render Network worker process is running.
    
    Returns:
        bool: True if worker is running
    """
    process = find_render_worker_process()
    return process is not None


def check_render_status() -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Check Render Network status.
    
    Returns:
        tuple: (success: bool, data: dict or None, error: str or None)
    """
    try:
        is_running = check_render_worker_running()
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'worker': {
                'status': 'running' if is_running else 'stopped',
                'process': find_render_worker_process()
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
            return True, data, "Render worker is not running"
        
        return True, data, None
        
    except Exception as e:
        logger.error(f"Error checking Render status: {e}")
        return False, None, f"Error checking Render status: {str(e)}"


def parse_render_status(data: Dict) -> Dict:
    """
    Parse Render Network status data for display.
    
    Args:
        data: Raw status data dictionary
        
    Returns:
        dict: Parsed status data
    """
    if not data:
        return {}
    
    parsed = {
        'worker_status': data.get('worker', {}).get('status', 'unknown'),
        'is_running': data.get('worker', {}).get('status') == 'running',
        'active_jobs': data.get('jobs', {}).get('active', 0),
        'completed_jobs': data.get('jobs', {}).get('completed', 0),
        'total_earnings': data.get('earnings', {}).get('total', 0.0),
        'pending_earnings': data.get('earnings', {}).get('pending', 0.0),
        'timestamp': data.get('timestamp', datetime.now().isoformat())
    }
    
    return parsed


def format_render_status(data: Dict) -> str:
    """
    Format Render Network status for Telegram display.
    
    Args:
        data: Parsed status data
        
    Returns:
        str: Formatted status message
    """
    if not data:
        return "❌ No Render Network status available."
    
    message_parts = []
    message_parts.append("🎨 *Render Network Status*\n")
    
    worker_status = data.get('worker_status', 'unknown')
    status_emoji = "🟢" if data.get('is_running', False) else "🔴"
    message_parts.append(f"• Worker Status: {status_emoji} {worker_status.capitalize()}")
    
    active_jobs = data.get('active_jobs', 0)
    completed_jobs = data.get('completed_jobs', 0)
    message_parts.append(f"• Active Jobs: `{active_jobs}`")
    message_parts.append(f"• Completed Jobs: `{completed_jobs}`")
    
    total_earnings = data.get('total_earnings', 0.0)
    pending_earnings = data.get('pending_earnings', 0.0)
    message_parts.append(f"• Total Earnings: `{total_earnings:.6f} RENDER`")
    if pending_earnings > 0:
        message_parts.append(f"• Pending Earnings: `{pending_earnings:.6f} RENDER`")
    
    timestamp = data.get('timestamp', datetime.now().isoformat())
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        formatted_time = timestamp
    message_parts.append(f"\n🕒 Last updated: `{formatted_time}`")
    
    return '\n'.join(message_parts)

