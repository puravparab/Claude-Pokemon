import os
import json
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv(override=True)

class Config:
	def __init__(self, config_path: str = "config.json"):
		self.config_path = config_path
		self.config = self._load_config()

	def _load_config(self) -> Dict[str, Any]:
		"""Load configuration from .env file"""
		# Default configuration
		return {
			"twitch_channel": os.getenv("TWITCH_CHANNEL", ""),
			"interval_minutes": int(os.getenv("INTERVAL_MINUTES", "10")),
			"openai_api_key": os.getenv("OPENAI_API_KEY", ""),
			"images_dir": os.getenv("IMAGES_DIR", "images"),
			"context_file": os.getenv("CONTEXT_FILE", "context.json"),
		}

	def get(self, key: str, default: Any = None) -> Any:
		"""Get configuration value by key."""
		return self.config.get(key, default)