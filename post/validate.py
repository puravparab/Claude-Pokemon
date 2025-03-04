import json
from typing import Dict, Any
from datetime import datetime

# def validate_response(response, image_path: str, timestamp: str, model: str, input_tokens: int, encoder):
# 	"""Validate and process LLM API response."""
		
# def sanitize_results(response: Dict[str, Any], image_path: str, timestamp: str, model: str) -> Dict[str, Any]:
# 	"""Validate and sanitize LLM response to ensure it matches the expected format."""

# def get_default_response(image_path: str, timestamp: str) -> Dict[str, Any]:
# 	"""Return a default response structure when analysis fails."""
# 	return {
# 		"image_path": image_path,
# 		"timestamp": timestamp,
# 		"model": None,
# 		"detailed_summary": "",
# 		"team_details": [],
# 		"score": 0,
# 		"estimated_location": "",
# 		"token_usage": {
# 			"input_tokens": 0,
# 			"output_tokens": 0,
# 			"total_tokens": 0,
# 		}
# 	} 

def count_tokens(text: str, encoder) -> int:
	"""Count tokens in text using the provided encoder."""
	return len(encoder.encode(text))