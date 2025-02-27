import os
import sys
import time
import logging
from datetime import datetime

from config import Config
from capture import TwitchCapture

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
	twitch_channel = config.get("twitch_channel")
	if not twitch_channel:
		logger.error("No Twitch channel provided in configuration")
		sys.exit(1)

	interval_minutes = config.get("interval_minutes", 10)
	images_dir = "output/images/"
	os.makedirs("output/images", exist_ok=True)
	context_file = "context.json"

	# Initialize components
	twitch = TwitchCapture(twitch_channel, images_dir)
	# context = ContextManager(context_file)
	# analyzer = GPTImageAnalyzer(openai_api_key)
	
	logger.info(f"Starting Twitch stream monitor for: {twitch_channel}")
	logger.info(f"Will capture screenshots every {interval_minutes} minutes")
    
	try:
		while True:
			try:
				# 1. Capture screenshot from Twitch
				image_path = twitch.capture_screenshot()
				
				# # 2. Get context from JSON file
				# logger.info("Loading context data...")
				# context_data = context.get_context()
				
				# # 3. Analyze image with GPT
				# logger.info("Analyzing image with GPT...")
				# summary_data = analyzer.analyze_image(image_path, context_data)
				
				# # 4. Save summary to context file
				# logger.info("Saving summary data...")
				# context.save_summary(summary_data)
				
				# # 5. Wait for next interval
				# next_time = datetime.now().timestamp() + (interval_minutes * 60)
				# logger.info(f"Next capture at {datetime.fromtimestamp(next_time).strftime('%H:%M:%S')}")
				time.sleep(interval_minutes * 60)
				
			except Exception as e:
				logger.error(f"Error in monitoring cycle: {e}")
				time.sleep(60)  # Wait a minute before retrying

	except KeyboardInterrupt:
		logger.info("Stopping Twitch monitor (received keyboard interrupt)")
	finally:
		capture.cleanup() # Clean up resources
	

if __name__ == "__main__":
  main()