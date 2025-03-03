from datetime import datetime, timezone
from post.context import Context

if __name__ == "__main__":
	context = Context()
	print(context.context_str)