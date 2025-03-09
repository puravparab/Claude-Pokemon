import os
import json
import base64
import logging
import requests
import tiktoken
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from .prompts import MONITOR_SYSTEM_PROMPT
from .validate import validate_response,sanitize_results, get_default_response, count_tokens

logger = logging.getLogger(__name__)

AVAILABLE_MODELS = [
	"google/gemini-2.0-flash-lite-preview-02-05:free",
	"google/gemini-2.0-flash-lite-001",
	"google/gemini-2.0-flash-001"
]

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
					"content": MONITOR_SYSTEM_PROMPT
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