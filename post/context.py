import json
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from .utils import get_relative_time

logger = logging.getLogger(__name__)

class Context:
	def __init__(
		self, 
		context_dir: str = "context/monitor", 
		context_filename: str = "context.jsonl", 
	):
		self.timestamp = datetime.now(timezone.utc)
		self.context_path = Path(context_dir) / context_filename
		self.context = self.get_context()
		self.context_str = self.context_to_string(self.context)

	def get_context(
		self,
		interval: timedelta = timedelta(minutes=5),
		limit: int = 20,
	) -> dict:
		"""Get context entries within a time window from the specified timestamp."""
		# Calculate window boundaries
		start_time = self.timestamp - interval
		end_time = self.timestamp

		context = []
		result = {
			"context": context,
			"count": 0,
			"avg_score": 0,
			"highest_score": {}
		}

		try:
			with open(self.context_path, 'r') as f:
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
				current_time = self.timestamp.timestamp()
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

	def context_to_string(self, context: dict = None) -> str:	
		"""Convert context data to a formatted string for use in LLM prompts."""

		if context is None:
			return ""
			
		if not context or "count" not in context or context["count"] == 0:
			return ""
			
		count = context["count"]
		avg_score = context["avg_score"]
		highest_score_event = context["highest_score"]
		highest_score_id = highest_score_event["id"]

		result = f"There are {count} recent events in the last 5 min with an average score of {avg_score:.2f} and event (id: {highest_score_id}) had the highest score {highest_score_event['score']}\n"
		result += "<recent_events>\n"

		# Add each event
		for event in context["context"]:
			result += "{\n"
			result += f'  "id": {event["id"]},\n'
			result += f'  "Time ago": "{event["relative_time"]}",\n'
			result += f'  "score": {event["score"]},\n'
			result += f'  "event_details": "{event["detailed_summary"]}",\n'
			
			# Handle team data
			team_data = event.get("team", [])
			if team_data:
				team_members = []
				for member in team_data:
					name = member.get("name", "unknown pokemon name")
					custom_name = member.get("custom_name", "unknown custom name")
					health = member.get("health", "unknown health status")
					team_members.append(f"{name} ({health})")
				team_str = ", ".join(team_members)
				result += f'  "team": "There are {len(team_data)} pokemons ({team_str})",\n'
			else:
				result += '  "team": "No team data available",\n'
					
			# Add location
			result += f'  "Current estimated location": "{event.get("estimated_location", "location unknown")}"\n'
			result += "}\n"
			
		result += "</recent_events>"

		return result