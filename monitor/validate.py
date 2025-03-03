import json
from typing import Dict, Any
from datetime import datetime

def validate_response(response, image_path: str, timestamp: str, model: str, input_tokens: int, encoder):
	"""Validate and process LLM API response."""
	# Check if response has the expected structure
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
		analysis_result = json.loads(content)
	except json.JSONDecodeError as json_err:
		raise ValueError(f"Failed to parse JSON: {json_err}")

	analysis_result['token_usage'] = {
		'input_tokens': input_tokens,
		'output_tokens': output_tokens,
		'total_tokens': input_tokens + output_tokens
	}

	return analysis_result
		
def sanitize_results(response: Dict[str, Any], image_path: str, timestamp: str, model: str) -> Dict[str, Any]:
	"""Validate and sanitize LLM response to ensure it matches the expected format."""
	validated = {
		"image_path": image_path,
		"timestamp": timestamp,
		"model": model,
		"detailed_summary": "",
		"team_details": [],
		"score": 1,
		"estimated_location": "Unknown",
		"token_usage": {
			"input_tokens": 0,
			"output_tokens": 0,
			"total_tokens": 0,
		}
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
			# Validate health
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
				validated["score"] = max(1, min(10, score))  # Clamp to 1-10 range
		except (ValueError, TypeError):
			pass
								
	# Validate estimated_location
	if "estimated_location" in response and isinstance(response["estimated_location"], str):
		validated["estimated_location"] = response["estimated_location"]
				
	# Validate token usage
	if "token_usage" in response and isinstance(response["token_usage"], dict):
		for key in ["input_tokens", "output_tokens", "total_tokens"]:
			if key in response["token_usage"] and isinstance(response["token_usage"][key], (int, float)):
				validated["token_usage"][key] = int(response["token_usage"][key])

	return validated

def get_default_response(image_path: str, timestamp: str) -> Dict[str, Any]:
	"""Return a default response structure when analysis fails."""
	return {
		"image_path": image_path,
		"timestamp": timestamp,
		"model": None,
		"detailed_summary": "",
		"team_details": [],
		"score": 0,
		"estimated_location": "",
		"token_usage": {
			"input_tokens": 0,
			"output_tokens": 0,
			"total_tokens": 0,
		}
	} 

def count_tokens(text: str, encoder) -> int:
	"""Count tokens in text using the provided encoder."""
	return len(encoder.encode(text))