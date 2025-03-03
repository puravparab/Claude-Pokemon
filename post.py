from datetime import datetime, timezone
from post.context import get_context

if __name__ == "__main__":
	current_time = datetime.now(timezone.utc)
	context = get_context(current_time)

	print(context)