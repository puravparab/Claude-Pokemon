import json
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from .utils import get_relative_time

logger = logging.getLogger(__name__)

def get_context(
	timestamp: datetime,
	interval: timedelta = timedelta(minutes=5),
	limit: int = 20,
	context_dir: str = "context/monitor", 
	context_filename: str = "context.jsonl"
) -> dict:
	"""Get context entries within a time window from the specified timestamp."""
	context_dir_path = Path(context_dir)
	context_path = context_dir_path / context_filename

	# Calculate window boundaries
	start_time = timestamp - interval
	end_time = timestamp

	context = []
	result = {
		"context": context,
		"count": 0,
		"avg_score": 0,
		"highest_score": {}
	}

	try:
		with open(context_path, 'r') as f:
			for line in f:
				entry = json.loads(line)
				entry_time = datetime.fromisoformat(entry["timestamp"])
				if start_time <= entry_time <= end_time and entry["detailed_summary"] != "":
					context.append(entry)

		# Sort by timestamp descending (most recent first)
		context.sort(key=lambda x: x["timestamp"], reverse=True)

		# Apply limit if specified
		if limit is not None:
			context = context[:limit]

		for i, entry in enumerate(context):
			entry["id"] = i + 1

			# Add relative timestamp to each entry
			current_time = timestamp.timestamp()
			entry_time = datetime.fromisoformat(entry["timestamp"]).timestamp()
			entry["relative_time"] = get_relative_time(current_time, entry_time)

		result["context"] = context
		result["count"] = len(context)

		if context:
			scores = [entry["score"] for entry in context]
			result["avg_score"] = sum(scores) / len(scores)
			highest_score_entry = max(context, key=lambda x: x["score"]) if context else {}
			result["highest_score"] = highest_score_entry
		
		return result
	except Exception as e:
		logger.error(f"Error retrieving context entries: {e}")
		return {}