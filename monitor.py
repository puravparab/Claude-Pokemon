import os
import sys
import glob
import time
import signal
import logging
from typing import Optional
from dotenv import load_dotenv
load_dotenv(override=True)

from monitor.server import Server
from monitor.capture import TwitchCapture
from monitor.llm import ImageAnalyzer
from monitor.context import save_to_context

# Configure logging
def setup_logging():
	# Create logs directory if it doesn't exist
	os.makedirs("logs", exist_ok=True)
	# Configure root logger
	logger = logging.getLogger()
	logger.setLevel(logging.INFO)
	# Create formatters
	formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
	# Setup console handler
	console_handler = logging.StreamHandler()
	console_handler.setFormatter(formatter)
	logger.addHandler(console_handler)
	# Setup file handler
	file_handler = logging.FileHandler("logs/monitor.log")
	file_handler.setFormatter(formatter)
	logger.addHandler(file_handler)
	return logger

logger = setup_logging()

SERVER_DIR = "monitor/stream"
IMAGES_DIR = "context/images"
DEFAULT_AGENT_BOOT_WAIT = "0" # mins
DEFAULT_MONITOR_INTERVAL = "0.5" # mins
MAX_IMAGES = 20 # Max images in context (roughly 10 mins worth of images)

class Monitor:
	def __init__(self):
		# Get environment variables with defaults
		self.twitch_channel = os.getenv("TWITCH_CHANNEL")
		if not self.twitch_channel:
			logger.error("TWITCH_CHANNEL environment variable is required")
			sys.exit(1)
					
		agent_boot_wait_str = os.getenv("AGENT_BOOT_WAIT", DEFAULT_AGENT_BOOT_WAIT)
		monitor_interval_str = os.getenv("MONITOR_INTERVAL", DEFAULT_MONITOR_INTERVAL)
		
			
		try:
			# Convert to minutes (float to allow for fractions)
			self.agent_boot_wait = float(agent_boot_wait_str)
			self.monitor_interval = float(monitor_interval_str)
			# Convert minutes to seconds
			self.agent_boot_wait_secs = self.agent_boot_wait * 60
			self.monitor_interval_secs = self.monitor_interval * 60

			self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
		except ValueError:
			logger.error("AGENT_BOOT_WAIT and MONITOR_INTERVAL must be numeric values")
			sys.exit(1)
					
		# Components
		self.server_port = 8001
		self.server: Optional[Server] = None
		self.capture: Optional[TwitchCapture] = None
		self.image_analyzer: Optional[ImageAnalyzer] = None
		# Flag to control the main loop
		self.running = False
        
	def initialize(self):
		"""Initialize server and capture components"""
		try:
			# Start the HTTP server
			logger.info("Starting HTTP server...")
			self.server = Server(port=self.server_port, directory=SERVER_DIR)
			self.server.start()
			
			# Initialize the Twitch capture
			logger.info("Initializing Twitch capture...")
			self.capture = TwitchCapture(server_port=self.server_port, images_dir=IMAGES_DIR)
			self.capture.init()
			logger.info(f"Initialization complete. Monitoring Twitch channel: {self.twitch_channel}")

			# Initialize the Image Analyzer with Openrouter
			logger.info("Initializing ImageAnalyzer...")
			self.image_analyzer = ImageAnalyzer(api_key=self.openrouter_api_key)
			logger.info(f"ImageAnalyzer initialized")

		except Exception as e:
			logger.error(f"Error during initialization: {e}")
			self.cleanup()
			sys.exit(1)

	def run(self):
		"""Run the monitoring loop"""
		self.running = True
		# Register signal handlers
		signal.signal(signal.SIGINT, self.handle_interrupt)
		signal.signal(signal.SIGTERM, self.handle_interrupt)
		
		# Wait before starting capture loop
		if self.agent_boot_wait_secs != 0:
			logger.info(f"Waiting {self.agent_boot_wait} minutes before starting capture...")
			time.sleep(self.agent_boot_wait_secs)

		try:
			# Main capture loop
			logger.info(f"Starting twitch capture loop (interval: {self.monitor_interval} minutes)")
			cleanup_count = 0  # Initialize image cleanup counter
			while self.running:
				try:
					# Capture screenshot
					screenshot_path = self.capture.capture_screenshot()

					# Analyze the screenshot
					analysis = self.image_analyzer.analyze_image(screenshot_path)

					# Save the analysis to context.json
					save_to_context(analysis)

					cleanup_count += 1  # Increment cleanup counter
					if cleanup_count >= 30: # Run cleanup when count reaches 30
						logger.info("Running image cleanup")
						self.cleanup_images()
						cleanup_count = 0 # Reset counter
						
					time.sleep(self.monitor_interval_secs)  # Wait until next capture
				except Exception as e:
					logger.error(f"Error during capture: {e}")
		finally:
			self.cleanup()
    
	def handle_interrupt(self, sig, frame):
		"""Handle keyboard interrupt or termination signal"""
		logger.info("Received interrupt signal, shutting down...")
		self.running = False
    
	def cleanup(self):
		"""Clean up resources"""
		logger.info("Cleaning up resources...")

		if self.capture:
			try:
				self.capture.cleanup()
				logger.info("Capture resources cleaned up")
			except Exception as e:
				logger.error(f"Error cleaning up capture: {e}")

		if self.server:
			try:
				self.server.stop()
				logger.info("Server stopped")
			except Exception as e:
				logger.error(f"Error stopping server: {e}")

	def cleanup_images(self):
		"""Keep only the latest MAX_IMAGES images in the images directory."""
		try:
			image_files = glob.glob(f"{IMAGES_DIR}/*.png") # Get all PNG files from the images directory
			image_files.sort(key=os.path.getmtime) # Sort files by modification time (newest last)

			# If we have more than MAX_IMAGES, remove the oldest ones
			if len(image_files) > MAX_IMAGES:
				files_to_remove = image_files[:-MAX_IMAGES]  # Keep the latest MAX_IMAGES
				for old_file in files_to_remove:
					try:
						os.remove(old_file)
						logger.debug(f"Removed old image: {old_file}")
					except Exception as e:
						logger.warning(f"Failed to remove old image {old_file}: {e}")
				
				logger.info(f"Cleaned up {len(files_to_remove)} old images, keeping the latest {MAX_IMAGES}")
		
		except Exception as e:
			logger.error(f"Error cleaning up old images: {e}")

if __name__ == "__main__":
	monitor = Monitor()
	monitor.initialize()
	monitor.run()