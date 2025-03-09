import os
import json
import logging
import requests
import tiktoken
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from .prompts import ANALYZE_CONTEXT_PROMPT, UPDATE_NOTES_PROMPT
from .validate import validate_response, sanitize_results, get_default_response, count_tokens

logger = logging.getLogger(__name__)

AVAILABLE_MODELS = [
	"google/gemini-2.0-flash-lite-preview-02-05:free",
	"google/gemini-2.0-flash-001",
]

class PostAnalyzer:
	"""Analyzes recent events and previous milestones by using LLM and decides whether a tweet should be created"""
	def __init__(self, api_key: str, model: str = None):
		self.api_key = api_key
		self.model = model if model in AVAILABLE_MODELS else AVAILABLE_MODELS[0]
		self.api_url = "https://openrouter.ai/api/v1/chat/completions"
		
		if not api_key:
			logger.error("No OpenRouter API key provided")
			raise ValueError("OpenRouter API key is required")

		self.encoder = tiktoken.encoding_for_model("gpt-4") # Initialize tiktoken encoder
            
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
		
	def analyze_context(self, context: str) -> Dict[str, Any]:
		"""Analyze a Twitch gameplay image and return structured data."""
		try:
			timestamp = datetime.now(timezone.utc).isoformat()
			headers = {
				"Authorization": f"Bearer {self.api_key}",
				"Content-Type": "application/json"
			}
			messages = [
				{
					"role": "system", 
					"content": ANALYZE_CONTEXT_PROMPT
				},
				{
					"role": "user",
					"content": [
						{
							"type": "text",
							"text": context
						}
					]
				}
			]
			input_tokens = self._count_tokens(messages)

			# Iterate through available models until request is processed
			for model in AVAILABLE_MODELS:
				self.model = model
				payload = {
					"model": model,
					"messages": messages,
					"response_format": {"type": "json_object"}
				}
				try:
					logger.info(f"Analyzing context (model: {model})")
					response = requests.post(self.api_url, json=payload, headers=headers)

					if response.status_code != 200:
						if response.status_code == 429:
							logger.warning(f"Rate limit exceeded for model {model}, trying next model")
							continue
						else:
							logger.error(f"HTTP error with model {model}: {response.status_code}")
							continue

					validated_result = validate_response(
						response.json(), 
						timestamp, 
						model, 
						input_tokens,
						self.encoder
					)
					result = sanitize_results(validated_result, timestamp, model)
					logger.info(f"Analysis of context successful!")
					return result
					
				except Exception as e:
					logger.error(f"Error with model {model}: {e}")
					continue

			logger.error("All models failed to analyze the context")
			return get_default_response(timestamp)
				
		except Exception as e:
			logger.error(f"Error analyzing context: {e}")
			return get_default_response(timestamp)

	def update_notes(self, context: str) -> str:
		"""Update notes based on context and existing notes."""
		try:
			timestamp = datetime.now(timezone.utc).isoformat()
			headers = {
				"Authorization": f"Bearer {self.api_key}",
				"Content-Type": "application/json"
			}
			messages = [
				{
					"role": "system", 
					"content": UPDATE_NOTES_PROMPT
				},
				{
					"role": "user",
					"content": [
						{
							"type": "text",
							"text": context
						}
					]
				}
			]
			input_tokens = self._count_tokens(messages)
					
			# Iterate through available models until request is processed
			for model in AVAILABLE_MODELS:
				self.model = model
				payload = {
					"model": model,
					"messages": messages
				}
				try:
					logger.info(f"Updating notes (model: {model})")
					response = requests.post(self.api_url, json=payload, headers=headers)

					if response.status_code != 200:
						if response.status_code == 429:
							logger.warning(f"Rate limit exceeded for model {model}, trying next model")
							continue
						else:
							logger.error(f"HTTP error with model {model}: {response.status_code}")
							continue

					# Extract content directly without validation
					if (
						"choices" in response.json() and 
						response.json()["choices"] and 
						"message" in response.json()["choices"][0] and
						"content" in response.json()["choices"][0]["message"]
					):
						content = response.json()["choices"][0]["message"]["content"]
						logger.info(f"Notes update successful!")
						return content
					else:
						logger.error(f"Invalid response structure from model {model}")
						continue
					
				except Exception as e:
					logger.error(f"Error with model {model}: {e}")
					continue

			logger.error("All models failed to update notes")
			return ""
					
		except Exception as e:
			logger.error(f"Error updating notes: {e}")
			return ""