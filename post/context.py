import json
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# rules
# if summary is "" do not include
# if length of context is 0 do not mnake llm call
# returns
#	llm response
# count
# average score
# relative time
# highest score 

def get_context(
	timestamp: datetime,
	interval: timedelta = timedelta(minutes=5),
	limit: Optional[int] = None,
	context_dir: str = "context/monitor", 
	context_filename: str = "context.jsonl"
) -> List[dict]:
	"""Get context entries within a time window from the specified timestamp."""
	context_dir_path = Path(context_dir)
	context_path = context_dir_path / context_filename

	# Calculate window boundaries
	start_time = timestamp - interval
	end_time = timestamp
	matching_entries = []

	with open(context_path, 'r') as f:
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