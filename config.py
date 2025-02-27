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
			"images_dir": os.getenv("IMAGES_DIR", "images"),
			"context_file": os.getenv("CONTEXT_FILE", "context.json"),
			# Openrouter API credentials
			"openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
			"openrouter_model": os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-lite-preview-02-05:free"),
			# X API credentials
			"twitter_api_key": os.getenv("X_API_KEY", ""),
			"twitter_api_secret": os.getenv("X_API_SECRET", ""),
			"twitter_access_token": os.getenv("X_ACCESS_TOKEN", ""),
			"twitter_access_secret": os.getenv("X_ACCESS_SECRET", ""),
			"twitter_enabled": os.getenv("X_ENABLED", "true").lower() == "true",
		}

	def get(self, key: str, default: Any = None) -> Any:
		"""Get configuration value by key."""
		return self.config.get(key, default)