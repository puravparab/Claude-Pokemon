from datetime import datetime, timezone
from post.context import get_context

if __name__ == "__main__":
	current_time = datetime.now(timezone.utc)
	entries = get_context(current_time)

	for i, entry in enumerate(entries):
		print(f"Image {i}:\nScore: {entry["score"]}, Location: {entry["estimated_location"]}\nSummary: {entry["detailed_summary"]}\n")