import os
import sys
import time
import logging
from datetime import datetime

from config import Config
from capture import TwitchCapture
from context import ContextManager
from llm import ImageAnalyzer
from tweet import TwitterPoster

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
	handlers=[
		logging.StreamHandler(sys.stdout),
		logging.FileHandler("logs/watch.log")
	]
)
logger = logging.getLogger(__name__)

def main():
	# Load configuration
	config = Config()
    
	# Get configuration values
	model = config.get("openrouter_model")
	twitch_channel = config.get("twitch_channel")
	if not twitch_channel:
		logger.error("No Twitch channel provided in configuration")
		sys.exit(1)

	interval_minutes = config.get("interval_minutes", 10)
	images_dir = "output/images"
	os.makedirs("output/images", exist_ok=True)
	context_file = "context.json"

	# Initialize components
	twitch = TwitchCapture(twitch_channel, images_dir)
	context = ContextManager(context_file)
	analyzer = ImageAnalyzer(config.get("openrouter_api_key"), model)

	# Initialize Twitter poster if enabled
	twitter_enabled = config.get("twitter_enabled", False)
	twitter = None
	if twitter_enabled:
		twitter = TwitterPoster(
			config.get("twitter_api_key"),
			config.get("twitter_api_secret"),
			config.get("twitter_access_token"),
			config.get("twitter_access_secret")
		)
		logger.info("Twitter posting is enabled")
	else:
		logger.info("Twitter posting is disabled")
	
	logger.info(f"Starting Twitch stream monitor for: {twitch_channel}")
	logger.info(f"Using model: {model}")
	logger.info(f"Will capture screenshots every {interval_minutes} minutes")
    
	try:
		while True:
			try:
				# 1. Capture screenshot from Twitch
				image_path = twitch.capture_screenshot()

				# 2. Get context from JSON file
				logger.info("Loading context data...")
				context_data = context.get_context(15)

				# 3. Analyze image with OpenRouter
				logger.info("Analyzing image ...")
				summary_data = analyzer.analyze_image(image_path, context_data)

				# 4. Save summary to context file
				logger.info("Saving summary data...")
				context.save_summary(summary_data, image_path, model)

				# 5. Post to Twitter if enabled and commentary is not empty
				if twitter_enabled and twitter and summary_data.get("commentary"):
					commentary = summary_data.get("commentary", "")
					if commentary.strip() != "":
						logger.info("Posting to Twitter...")
						twitter.post_with_image(commentary, image_path)
					else:
						logger.info("Commentary is empty, skipping Twitter post")

				# 6. Sleep for interval_minutes minutes
				time.sleep(interval_minutes * 60)
				
			except Exception as e:
				logger.error(f"Error in monitoring cycle: {e}")
				time.sleep(60)  # Wait a minute before retrying

	except KeyboardInterrupt:
		logger.info("Stopping Twitch monitor (received keyboard interrupt)")
	finally:
		twitch.cleanup()

if __name__ == "__main__":
  main()