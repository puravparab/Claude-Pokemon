import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def save_to_context(
	analysis_result: dict,
	context_dir: str = "context/monitor", 
	context_filename: str = "context.jsonl"
) -> None:
	"""Save analysis result to context file using JSON Lines format.
		
	Args:
		analysis_result: Dictionary containing analysis data to save
		root_dir: Root directory for context data
		monitor_dir: Subdirectory for monitor data
		context_filename: Name of the context file
	"""
	# Ensure directory exists
	context_dir_path = Path(context_dir)
	context_dir_path.mkdir(parents=True, exist_ok=True)
	context_path = context_dir_path / context_filename

	# Append the data as json line
	with open(context_path, 'a') as f:
		f.write(json.dumps(analysis_result) + '\n')

	logger.info(f"Analysis saved to {context_path}")