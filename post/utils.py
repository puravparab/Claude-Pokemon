import time

def get_relative_time(current_time: float, past_time: float) -> str:
	"""
	Convert time difference between two UTC timestamps into a human-readable relative time string.

	Args:
		current_time (float): Current UTC timestamp
		past_time (float): Past UTC timestamp to compare against
	"""
	diff_seconds = int(current_time - past_time)
	diff_minutes = diff_seconds // 60 # Convert to minutes
	if diff_seconds < 60:
		return "1 min ago"
	elif diff_minutes < 60:
		return f"{diff_minutes} min ago"
	else:
		hours = diff_minutes // 60
		return f"{hours} hr ago"