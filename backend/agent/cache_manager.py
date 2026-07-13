"""
cache_manager.py — Simple in-memory TTL caching for tool executions.

WHY:  Avoids redundant Google API calls for data that rarely changes.
      (e.g., calendar list, drive files). 
"""

import time
import logging
from typing import Any, Optional, Dict, Tuple

logger = logging.getLogger(__name__)

# In-memory dictionary: tool_name -> (timestamp, data)
_CACHE: Dict[str, Tuple[float, Any]] = {}

# Configurable TTLs per service (in seconds)
# 5 minutes = 300 seconds
TTL_CONFIG = {
    "calendar_today": 300,
    "calendar_week": 300,
    "calendar_upcoming": 300,
    "drive_list": 300,
    "docs_list": 300,
    "sheets_list": 300,
    "slides_list": 300,
    "gmail_list": 60,   # Shorter TTL for emails
    "gmail_unread": 60,
    "profile_info": 3600, # 1 hour
}

def get_cached(tool_name: str) -> Optional[Any]:
    """Return cached data if valid, otherwise None."""
    if tool_name not in _CACHE:
        return None
        
    ttl = TTL_CONFIG.get(tool_name, 0)
    if ttl == 0:
        return None # Not cacheable
        
    timestamp, data = _CACHE[tool_name]
    if time.time() - timestamp <= ttl:
        logger.info("Cache HIT for %s", tool_name)
        return data
        
    logger.info("Cache EXPIRED for %s", tool_name)
    del _CACHE[tool_name]
    return None

def set_cached(tool_name: str, data: Any) -> None:
    """Store data in cache if the tool is configured for caching."""
    if tool_name in TTL_CONFIG:
        _CACHE[tool_name] = (time.time(), data)
        logger.info("Cache SET for %s", tool_name)
