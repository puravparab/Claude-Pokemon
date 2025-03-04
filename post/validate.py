import json
from typing import Dict, Any
from datetime import datetime

def validate_response(response, timestamp: str, model: str, input_tokens: int, encoder):
	"""Validate and process LLM API response for post agent."""
	if (
		"choices" not in response or 
		not response["choices"] or 
		"message" not in response["choices"][0] or
		"content" not in response["choices"][0]["message"]
	):
		raise ValueError("Invalid response structure")

	content = response["choices"][0]["message"]["content"]
	output_tokens = count_tokens(content, encoder)

	try:
		post_result = json.loads(content)
	except json.JSONDecodeError as json_err:
		raise ValueError(f"Failed to parse JSON: {json_err}")

	post_result['token_usage'] = {
		'input_tokens': input_tokens,
		'output_tokens': output_tokens,
		'total_tokens': input_tokens + output_tokens
	}
	return post_result
        
def sanitize_results(response: Dict[str, Any], timestamp: str, model: str) -> Dict[str, Any]:
	"""Validate and sanitize LLM response to ensure it matches the expected format for post agent."""
	validated = {
		"timestamp": timestamp,
		"model": model,
		"commentary": "",
		"score": 0,
		"post": False,
		"image_id": None,
		"token_usage": {
				"input_tokens": 0,
				"output_tokens": 0,
				"total_tokens": 0,
		}
	}

	# Validate commentary
	if "commentary" in response and isinstance(response["commentary"], str):
		validated["commentary"] = response["commentary"]
						
	# Validate score (must be 0-10 integer)
	if "score" in response:
		try:
			score = int(response["score"])
			if 0 <= score <= 10:
				validated["score"] = score
			else:
				validated["score"] = max(0, min(10, score))  # Clamp to 0-10 range
		except (ValueError, TypeError):
			pass
						
	# Validate post flag
	if "post" in response and isinstance(response["post"], bool):
		validated["post"] = response["post"]
						
	# Validate image_id
	if "image_id" in response and (isinstance(response["image_id"], int) or response["image_id"] is None):
		validated["image_id"] = response["image_id"]
						
	# Validate token usage
	if "token_usage" in response and isinstance(response["token_usage"], dict):
		for key in ["input_tokens", "output_tokens", "total_tokens"]:
			if key in response["token_usage"] and isinstance(response["token_usage"][key], (int, float)):
				validated["token_usage"][key] = int(response["token_usage"][key])

	return validated

def get_default_response(timestamp: str) -> Dict[str, Any]:
	"""Return a default response structure when analysis fails."""
	return {
		"timestamp": timestamp,
		"model": None,
		"commentary": "",
		"score": 0,
		"post": False,
		"image_id": None,
		"token_usage": {
			"input_tokens": 0,
			"output_tokens": 0,
			"total_tokens": 0,
		}
	} 

def count_tokens(text: str, encoder) -> int:
	"""Count tokens in text using the provided encoder."""
	return len(encoder.encode(text))