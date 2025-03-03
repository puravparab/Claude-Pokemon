import json
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def get_context(
	timestamp: datetime,
	interval: timedelta = timedelta(minutes=5),
	limit: Optional[int] = None,
	root_dir: Path = Path("context"),
	monitor_dir: str = "monitor", 
	context_filename: str = "context.jsonl"
) -> List[dict]:
	"""Get context entries within a time window from the specified timestamp.

	Args:
		timestamp: Reference timestamp to center the window around
		interval: Time interval to look back from timestamp (default: 5 minutes)
		limit: Optional max number of entries to return (most recent first)
		root_dir: Root directory for context data
		monitor_dir: Subdirectory for monitor data 
		context_filename: Name of the context file
		
	Returns:
		List of context entries as dictionaries within the time window
	"""
	context_dir = root_dir / monitor_dir
	context_file = context_dir / context_filename

	# Calculate window boundaries
	start_time = timestamp - interval
	end_time = timestamp
	matching_entries = []

	with open(context_file, 'r') as f:
		for line in f:
			entry = json.loads(line)
			entry_time = datetime.fromisoformat(entry["timestamp"])
			if start_time <= entry_time <= end_time:
				matching_entries.append(entry)

	# Sort by timestamp descending (most recent first)
	matching_entries.sort(key=lambda x: x["timestamp"], reverse=True)

	# Apply limit if specified
	context = matching_entries
	if limit is not None:
		context = matching_entries[:limit]

	return context