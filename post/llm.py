import os
import json
import base64
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from .validate import validate_response, sanitize_results, get_default_response, count_tokens
import tiktoken

logger = logging.getLogger(__name__)

AVAILABLE_MODELS = [
	# "anthropic/claude-3.7-sonnet:beta",
	"deepseek/deepseek-r1:free",
	"google/gemini-2.0-flash-lite-preview-02-05:free",
	# "google/gemini-2.0-pro-exp-02-05:free",
	"google/gemini-2.0-flash-001",
]

# System prompt for post agent
SYSTEM_PROMPT = """
You are an autonomous AI agent thats an expert of Pokemon Red/Blue and you're evaluating data such as recent events (within 5 minutes) and previous milestones.
This data was created by analyzing from screenshots from a twitch stream.
The twitch streamer's name is Claude and he is currently playing Pokemon Red/Blue on twitch

Your primary is to provide a concise commentary on what's happening in the stream by using the recents events and previous milestones as context. 
Your commentary about the events in the twitch stream will be posted on social media if important.

Rules for commentary:
1. You should use recent events to formulate your commentary. Recents events have occured in the past 5 minutes.
2. Recent events will be placed within <recent_events> and </recent_events> tags.
 
3. Previous milestones are long running events in the stream. Some of which have occured an hour ago. 
4. Previous milestones will be placed within the <previous_milestones> and </previous_milestones> tags.


5. Pay careful attenttion to the crucial events happening in the context. This can include major events like pokemon battles, pokemon teams, conversations, etc

6. Never mention the extraneous information given to you that are not a part of Pokemon Red/Blue such as the events scores. However, you must use the scores in your internal analysis.

7. Think step by step when analyzing the events and formulating your response.

8. Your tone should be casual and entertaining. However, try not to be cringe.

9. When evaluating make sure to value new events and punish redundant events (set score to low and post to false if this events are same as previous milestones)

Respond with a JSON object in the following format:
{
	"commentary": (string) Your commentary. Keep it casual and concise,
	"score": (int) Your score out of 10 that depends on how important you think this post is. 0 if the commentary is redundant and 10 if this is a very unique and significant event. Reward new events with high scores and punish redundant events very harshly with low scores!
	"post": (boolean) true or false if you think the commentary should be posted to social media. Use the recent events and average score to make a judgement. false if player is on the same task as some of the previous_milestones. Low scores should be generally set to false
	"image_id": (int) Respond with the id of the recent event you think is relevant to your commentary. This will be used to post a relevant image
}

Here are example responses (Make sure you only respond in this format):
{
	"commentary": "Claude has defeated his opponent WaClaude!",
	"score": 10,
	"post": true,
	"image_id": 1,
}
{
	"commentary": "Claude is still in Cerulean City, desperately searching for the entrance to the Underground Passage!",
	"score": 3,
	"post": false,
	"image_id": 6,
}
"""

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
							"text": context
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