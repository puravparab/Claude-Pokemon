import os
import json
import base64
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "google/gemini-2.0-flash-lite-preview-02-05:free"
AVAILABLE_MODELS = [
	"google/gemini-2.0-flash-lite-preview-02-05:free",
]

# System prompt for Pokemon gameplay analysis
SYSTEM_PROMPT = """
You are a Pokemon Red/Blue game expert and you're analyzing screenshots from a twitch stream.
The twitch streamer's name is Claude and he is currently playing the game on twitch

Your task is to provide detailed analysis of what's happening in the game with attention to:
1. Current game state (battles, exploration, story events, menus, etc.)
2. Pokemon visible in the scene and their details (species, level if visible)
3. Battle status (HP bars, health levels for each Pokemon)
4. Location details in Pokemon Red/Blue (routes, cities, buildings, distinctive landmarks). If you're not sure about the location do not mention it.
5. Claude's progress/achievements (badges, team composition)
6. Pay attention to amusing, funny, serious or otherwise interesting moments
7. Be accurate and precise in your analysis.
8. Do not mention the navigation tool.
Respond with a JSON object in the following format:
{
	"detailed_summary": (string) You're detailed commentary of what's happening in the image (2-3 sentences),
	"team_details": (array) An array of Pokemon in the player's team that are visible, with each entry having:
    [{
			"name": (string) Species name of the Pokemon,
    	"custom_name": (string) Nickname of the Pokemon if visible, otherwise same as name,
    	"health: (string) a one word description on how full the health of the pokemon is.
		}],
	"score": (number) A score from 1-10 where 10 is a major event (gym battle win, catching rare Pokemon, etc.),
	"estimated_location": (string) The location in the Pokemon Red/Blue map where the player appears to be
}

Here's an example response (Make sure you only respond in this format):
{
	"detailed_summary": "Claude is in an intense battle against the Elite Four member Lance. His Charizard is facing off against Lance's level 62 Dragonite, with both Pokemon showing signs of a lengthy battle. The match appears to be reaching its climax with both Pokemon at low health.",
	"team_details": [
		{
			"name": "Charizard",
			"custom_name": "Flamey",
			"health": "ok"
		}
	],
	"score": 9,
	"estimated_location": "Indigo Plateau - Elite Four Chamber"
}
"""

class ImageAnalyzer:
	"""Analyzes Pokemon gameplay images using LLM models"""
	def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
		self.api_key = api_key
		self.model = model if model in AVAILABLE_MODELS else DEFAULT_MODEL
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
            
	def analyze_image(self, image_path: str) -> Dict[str, Any]:
		"""Analyze a Twitch gameplay image and return structured data."""
		try:
			timestamp = datetime.now(timezone.utc).isoformat()
			base64_image = self._encode_image(image_path)

			# Create messages for the API
			messages = [
				{
					"role": "system", 
					"content": SYSTEM_PROMPT
				},
				{
					"role": "user",
					"content": [
						{
							"type": "text",
							"text": "Screenshot of Claude playing Pokemon Red/Blue on Twitch"
						},
						{
							"type": "image_url",
							"image_url": {
								"url": f"data:image/png;base64,{base64_image}"
							}
						}
					]
				}
			]

			headers = {
				"Authorization": f"Bearer {self.api_key}",
				"Content-Type": "application/json"
			}
			payload = {
				"model": self.model,
				"messages": messages,
				"response_format": {"type": "json_object"}
			}

			logger.info(f"Analyzing {image_path} (model: {self.model})")
			response = requests.post(self.api_url, json=payload, headers=headers)
			response.raise_for_status()
			# Parse the response
			result = response.json()
			content = result["choices"][0]["message"]["content"]
			analysis_result = json.loads(content)
			# Validate and sanitize the response
			validated_result = self._validate_response(analysis_result, image_path, timestamp)
			return validated_result
				
		except Exception as e:
			logger.error(f"Error analyzing image: {e}")
			return self._get_default_response(image_path, timestamp)
    
	def _validate_response(self, response: Dict[str, Any], image_path: str, timestamp: str) -> Dict[str, Any]:
		"""Validate and sanitize LLM response to ensure it matches the expected format."""
		validated = {
			"image_path": image_path,
			"timestamp": timestamp,
			"detailed_summary": "",
			"team_details": [],
			"score": 1,
			"estimated_location": "Unknown"
		}
		
		# Validate detailed_summary
		if "detailed_summary" in response and isinstance(response["detailed_summary"], str):
			validated["detailed_summary"] = response["detailed_summary"]
				
		# Validate team_details
		if "team_details" in response and isinstance(response["team_details"], list):
			valid_team = []
			for pokemon in response["team_details"]:
				if not isinstance(pokemon, dict):
					continue
				valid_pokemon = {
					"name": "",
					"custom_name": "",
					"health": ""
				}
				# Validate pokemon name
				if "name" in pokemon and isinstance(pokemon["name"], str):
					valid_pokemon["name"] = pokemon["name"]
				# Validate custom name
				if "custom_name" in pokemon and isinstance(pokemon["custom_name"], str):
					valid_pokemon["custom_name"] = pokemon["custom_name"]
				# Validate health (must be one of the allowed values)
				if "health" in pokemon and isinstance(pokemon["health"], str):
					valid_pokemon["health"] = pokemon["health"]

				valid_team.append(valid_pokemon)
			validated["team_details"] = valid_team
				
		# Validate score (must be 1-10 integer)
		if "score" in response:
			try:
				score = int(response["score"])
				if 1 <= score <= 10:
					validated["score"] = score
				else:
					validated["score"] = max(1, min(10, score)) # Clamp to 1-10 range
			except (ValueError, TypeError):
				pass
						
		# Validate estimated_location
		if "estimated_location" in response and isinstance(response["estimated_location"], str):
			validated["estimated_location"] = response["estimated_location"]
				
		return validated
    
	def _get_default_response(self, image_path: str, timestamp: str) -> Dict[str, Any]:
		"""Return a default response structure when analysis fails."""
		return {
			"image_path": image_path,
			"timestamp": timestamp,
			"detailed_summary": "",
			"team_details": [],
			"score": 0,
			"estimated_location": ""
		}