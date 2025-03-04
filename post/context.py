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
		posts_dir: str = "context/posts", 
		posts_filename: str = "posts.jsonl"
	):
		self.timestamp = datetime.now(timezone.utc)
		self.context_path = Path(context_dir) / context_filename
		self.posts_dir = Path(posts_dir)
		self.posts_path = self.posts_dir / posts_filename
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
			team_data = event.get("team_details", [])
			if team_data:
				team_members = []
				for member in team_data:
					name = member.get("name", "unknown pokemon name")
					custom_name = member.get("custom_name", "unknown custom name")
					health = member.get("health", "unknown health status")
					team_members.append(f"{name}/{custom_name} ({health})")
				team_str = ", ".join(team_members)
				result += f'  "team": "There are {len(team_data)} pokemons ({team_str})",\n'
			else:
				result += '  "team": "No team data available",\n'
					
			# Add location
			result += f'  "Current estimated location": "{event.get("estimated_location", "location unknown")}"\n'
			result += "}\n"
			
		result += "</recent_events>"

		return result

	def save_post(
		self,
		response: dict
	) -> str:
		"""Save the LLM response to a posts jsonl and return the image path."""
		# Ensure the posts directory exists
		self.posts_dir.mkdir(parents=True, exist_ok=True)

		# Find the image path based on image_id
		image_path = ""
		if self.context and "context" in self.context and len(self.context["context"]) > 0:
			image_id = response.get("image_id", 0)
			
			# Find the context entry with matching ID
			for entry in self.context["context"]:
				if entry.get("id") == image_id and "image_path" in entry:
					image_path = entry["image_path"]
					response["image_path"] = image_path
					break
			
		# Append the data as a JSON line
		try:
			with open(self.posts_path, 'a') as f:
				f.write(json.dumps(response) + '\n')
			logger.info(f"Post saved to {self.posts_path}")
		except Exception as e:
			logger.error(f"Error saving post to {self.posts_path}: {e}")
			
		return image_path