import os
import json
import base64
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ImageAnalyzer:
	"""Analyzes images using models from OpenRouter"""

	def __init__(self, api_key: str, model: str = "google/gemini-2.0-flash-lite-preview-02-05:free"):
		self.api_key = api_key
		self.model = model
		self.api_url = "https://openrouter.ai/api/v1/chat/completions"
		
		if not api_key:
			logger.error("No OpenRouter API key provided")
			raise ValueError("OpenRouter API key is required")
			
	def _encode_image(self, image_path: str) -> str:
		"""Encode image to base64."""
		if not os.path.exists(image_path):
			raise FileNotFoundError(f"Image file not found: {image_path}")
			
		with open(image_path, "rb") as image_file:
			return base64.b64encode(image_file.read()).decode('utf-8')
			
	def analyze_image(self, image_path: str, context_data: List[Dict[str, Any]]) -> Dict[str, Any]:
		"""Analyze an image using OpenRouter API and return structured data."""
		try:
			# Encode image
			base64_image = self._encode_image(image_path)
			
			# Get recent context entries and build context string from previous data
			context_string = self._build_context_string(context_data)
			
			# Create system prompt
			system_prompt = """
			You are a Pokemon game expert and enthusiastic commentator analyzing screenshots of Pokemon Red/Blue gameplay. 
			The current player's name is Claude.
			
			Your task is to provide engaging and informative analysis of what's happening in the game with attention to:
			1. Current game state (battles, exploration, story events, menus, etc.)
			2. Pokemon visible in the scene and their details (species, level if visible)
			3. Battle status (HP bars, move selection, effects)
			4. Location details (routes, cities, buildings, distinctive landmarks)
			5. Claude's progress/achievements (badges, team composition, significant events)
			6. Any unique or rare occurrences (shiny Pokemon, rare encounters, critical moments)
			7. If you see something amusing, mention it!
			8. Do not refer to anything mentioned next to "using tool"
			
			Respond with a JSON object containing these fields:
			- commentary: A brief, enthusiastic commentary about what's happening (1-2 sentences) - be entertaining!
			- description: A detailed description of everything visible in the image (3-4 sentences)
			- unique: (True/False) Boolean indicating if this event appears unique/significant compared to previous events
			"""
			
			# Format image URL according to OpenRouter docs
			image_url = f"data:image/png;base64,{base64_image}"
			
			# Create messages for the API
			messages = [
				{
					"role": "system", 
					"content": system_prompt
				},
				{
					"role": "user",
					"content": [
						{
							"type": "text",
							"text": f"Analyze this Pokemon gameplay screenshot. {context_string}"
						},
						{
							"type": "image_url",
							"image_url": {
								"url": image_url
							}
						}
					]
				}
			]
			
			# Make the API request
			headers = {
				"Authorization": f"Bearer {self.api_key}",
				"Content-Type": "application/json"
			}
			
			payload = {
				"model": self.model,
				"messages": messages,
				"response_format": {"type": "json_object"}
			}
			
			logger.info(f"Analyzing screenshot {image_path} (model: {self.model})")
			response = requests.post(self.api_url, json=payload, headers=headers)
			response.raise_for_status()
			
			# Parse the response
			result = response.json()
			content = result["choices"][0]["message"]["content"]
			analysis_result = json.loads(content)
			
			# Ensure all required fields are present
			required_fields = ["commentary", "description", "unique"]
			for field in required_fields:
				if field not in analysis_result:
					analysis_result[field] = "" if field != "unique" else False
					
			return analysis_result
			
		except Exception as e:
			logger.error(f"Error analyzing image: {e}")
			# Return a simple error response
			return {
				"commentary": "",
				"description": "",
				"unique": False
			}
			
	def _build_context_string(self, context_data: List[Dict[str, Any]]) -> str:
		"""Build a context string from previous data."""
		if not context_data:
			return "This is the first screenshot being analyzed."
			
		now = datetime.now(timezone.utc)
		context_string = "Here's are the previous events in reverse chronological order\n"
		
		for idx, item in enumerate(context_data):
			timestamp_str = item.get("timestamp", "")
			description = item.get("description", "")
			
			# Calculate relative time
			time_ago = ""
			try:
				timestamp_dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
				time_diff = now - timestamp_dt
				# Convert to appropriate unit
				minutes = time_diff.total_seconds() / 60
				if minutes < 2:
					time_ago = "1 minute ago"
				elif minutes < 60:
					time_ago = f"{int(minutes)} minutes ago"
				elif minutes < 120:
					time_ago = "1 hour ago"
				elif minutes < 1440:  # less than a day
					time_ago = f"{int(minutes / 60)} hours ago"
				elif minutes < 2880:  # less than 2 days
					time_ago = "1 day ago"
				else:
					time_ago = f"{int(minutes / 1440)} days ago"
			except:
				time_ago = f"at {timestamp_str}"
				
			context_string += f"{idx+1}. {time_ago}: {description}\n"
			
		return context_string