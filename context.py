import os
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ContextManager:
	"""Manages the context file for storing image analysis results."""

	def __init__(self, context_file: str = "context.json"):
		self.context_file = context_file
		self.context = self._load_context()
		
	def _load_context(self) -> List[Dict[str, Any]]:
		"""Load context from JSON file or create empty context if file doesn't exist."""
		if os.path.exists(self.context_file):
			try:
				with open(self.context_file, "r") as f:
					return json.load(f)
			except json.JSONDecodeError:
				logger.warning(f"Error parsing {self.context_file}, creating new context")
				return []
		else:
			logger.info(f"Context file {self.context_file} not found, creating new context")
			return []

	def get_context(self, max_items: int = 5) -> List[Dict[str, Any]]:
		"""Get the most recent context items."""
		return self.context[-max_items:] if self.context else []

	def save_summary(self, summary_data: Dict[str, Any], image_path: str = None, model: str = None) -> None:
		"""Save a new summary to the context file."""
		# Add timestamp if not provided
		if "timestamp" not in summary_data:
			summary_data["timestamp"] = datetime.now(timezone.utc).isoformat()
			
		# Count previous events
		summary_data["num_previous_events"] = 5

		# Add image path
		if image_path:
			summary_data["image_path"] = image_path

		# Add model information
		if model:
			summary_data["model"] = model

		# Append to context
		self.context.append(summary_data)

		# Save to file
		with open(self.context_file, "w") as f:
			json.dump(self.context, f, indent=2)
			
		logger.info(f"Saved summary to {self.context_file}")