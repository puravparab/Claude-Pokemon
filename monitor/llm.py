import os
import json
import base64
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from .validate import validate_response,sanitize_results, get_default_response, count_tokens
import tiktoken

logger = logging.getLogger(__name__)

AVAILABLE_MODELS = [
	"google/gemini-2.0-flash-lite-preview-02-05:free",
	"google/gemini-2.0-flash-lite-001",
	"google/gemini-2.0-flash-001"
]

# System prompt for ImaageAnalyzer
SYSTEM_PROMPT = """
You are a Pokemon Red/Blue game expert and you're analyzing screenshots from a twitch stream.
The twitch streamer's name is Claude and he is currently playing the game on twitch

Your task is to provide detailed_summary analyis of what's happening in the game with attention to:
1. Current game state (battles, exploration, story events, menus, etc.)
2. Battle status (HP bars, health levels for each Pokemon)
3. Location details in Pokemon Red/Blue (routes, cities, buildings, distinctive landmarks).
4. Claude's progress/achievements (badges, team composition)

Rules for detailed_summary
1. Pay attention to amusing, funny, serious or otherwise interesting moments
2. If you're not sure about the location do not mention it.
3. Be accurate and precise in your analysis.
4. Do not mention the any tools on the left panel that are not part of Pokemon Red/Blue. Do not mention the navigation tool.
5. Pay careful attention to conversations in the game
6. Pay attention to decisions being made by the Player
7. Do not mention coordinates in the detailed_summary but factor it into your internal analysis of the image.
8. Pay attention to the Pokemon visible in the scene and their details (species, level if visible)

Respond with a JSON object in the following format:
{
	"detailed_summary": (string) You're detailed commentary of what's happening in the image (2-3 sentences),
	"team_details": (array) An array of Pokemon in the player's team that are visible, with each entry having:
    [{
			"name": (string) Species name of the Pokemon,
    	"custom_name": (string) Nickname of the Pokemon if visible, otherwise same as name,
    	"health: (string) a one word description on how full the health of the pokemon is.
		}],
	"score": (number) A score from 1-10 where 10 is a major event and 1 is mundane event (important events can be gym battle win, catching rare Pokemon, pokemon battles, other events, etc.),
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
	def __init__(self, api_key: str, model: str = None):
		self.api_key = api_key
		self.model = model if model in AVAILABLE_MODELS else AVAILABLE_MODELS[0]
		self.api_url = "https://openrouter.ai/api/v1/chat/completions"
		
		if not api_key:
			logger.error("No OpenRouter API key provided")
			raise ValueError("OpenRouter API key is required")

		self.encoder = tiktoken.encoding_for_model("gpt-4") # Initialize tiktoken encoder
		
	def _encode_image(self, image_path: str) -> str:
		"""Encode image to base64."""
		if not os.path.exists(image_path):
			raise FileNotFoundError(f"Image file not found: {image_path}")
				
		with open(image_path, "rb") as image_file:
			return base64.b64encode(image_file.read()).decode('utf-8')
            
	def _count_tokens(self, messages: List[Dict]) -> int:
		"""Count input and output tokens using tiktoken."""
		token_count = 0
		for message in messages:
			if isinstance(message.get('content'), str):
				token_count += count_tokens(message['content'], self.encoder)
			elif isinstance(message.get('content'), list):
				for content in message['content']:
					if content['type'] == 'text':
						token_count += count_tokens(content['text'], self.encoder)
		return token_count
		
	def analyze_image(self, image_path: str) -> Dict[str, Any]:
		"""Analyze a Twitch gameplay image and return structured data."""
		try:
			timestamp = datetime.now(timezone.utc).isoformat()
			base64_image = self._encode_image(image_path)
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

			input_tokens = self._count_tokens(messages)

			headers = {
				"Authorization": f"Bearer {self.api_key}",
				"Content-Type": "application/json"
			}
			
			# Iterate through available models until request is processed
			for model in AVAILABLE_MODELS:
				payload = {
					"model": model,
					"messages": messages,
					"response_format": {"type": "json_object"}
				}
				try:
					logger.info(f"Analyzing {image_path} (model: {model})")
					response = requests.post(self.api_url, json=payload, headers=headers)

					if response.status_code != 200:
						if response.status_code == 429:
							logger.warning(f"Rate limit exceeded for model {model}, trying next model")
							continue
						else:
							logger.error(f"HTTP error with model {model}: {response.status_code}")
							continue

					# Let validate_api_response handle all the validation
					validated_result = validate_response(
						response.json(), 
						image_path, 
						timestamp, 
						model, 
						input_tokens,
						self.encoder
					)
					
					# Sanitize the response
					result = sanitize_results(validated_result, image_path, timestamp, model)
					logger.info(f"Analysis of {image_path} successful!")
					return result
					
				except Exception as e:
					logger.error(f"Error with model {model}: {e}")
					continue

			logger.error("All models failed to analyze the image")
			return get_default_response(image_path, timestamp)
				
		except Exception as e:
			logger.error(f"Error analyzing image: {e}")
			return get_default_response(image_path, timestamp)