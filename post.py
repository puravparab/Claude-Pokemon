import os
import sys
import time
import signal
import logging
from typing import Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(override=True)

from post.llm import PostAnalyzer
from post.context import Context
from post.tweet import TwitterClient

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
	file_handler = logging.FileHandler("logs/post.log")
	file_handler.setFormatter(formatter)
	logger.addHandler(file_handler)
	return logger

logger = setup_logging()

DEFAULT_AGENT_BOOT_WAIT = "0" # mins
DEFAULT_POST_INTERVAL = "5" # mins

class PostAgent:
	def __init__(self):
		# Get environment variables with defaults
		agent_boot_wait_str = os.getenv("AGENT_BOOT_WAIT", DEFAULT_AGENT_BOOT_WAIT)
		post_interval_str = os.getenv("POST_INTERVAL", DEFAULT_POST_INTERVAL)
		
		try:
			# Convert to minutes
			self.agent_boot_wait = float(agent_boot_wait_str)
			self.post_interval = float(post_interval_str)
			# Convert minutes to seconds
			self.agent_boot_wait_secs = self.agent_boot_wait * 60
			self.post_interval_secs = self.post_interval * 60
			
			# Openrouter credentials
			self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

			# X API credentials
			self.x_api_key = os.getenv("X_API_KEY")
			self.x_api_secret = os.getenv("X_API_SECRET")
			self.x_access_token = os.getenv("X_ACCESS_TOKEN")
			self.x_access_secret = os.getenv("X_ACCESS_SECRET")
			self.x_enabled = os.getenv("X_ENABLED", "false").lower() == "true"
				
		except ValueError:
			logger.error("AGENT_BOOT_WAIT and POST_INTERVAL must be numeric values")
			sys.exit(1)

		# Flag to control the main loop
		self.running = False

	def initialize(self):
		"""Initialize the posting agent"""
		try:
			logger.info("Initializing posting agent...")
			logger.info(f"Post interval set to {self.post_interval} minutes")

			# Initialize Twitter if enabled
			if self.x_enabled:
				if all([self.x_api_key, self.x_api_secret, self.x_access_token, self.x_access_secret]):
					logger.info("X/Twitter posting enabled!")
					self.x_client = TwitterClient(
						self.x_api_key, 
						self.x_api_secret, 
						self.x_access_token, 
						self.x_access_secret
					)
				else:
					logger.warning("X/Twitter posting disabled as credentials are incomplete")
					self.x_enabled = False
			else:
				logger.info("X/Twitter posting disabled")

			# Initialize the PostAnalyzer with Openrouter
			logger.info("Initializing PostAnalyzer...")
			self.post_analyzer = PostAnalyzer(api_key=self.openrouter_api_key)
			logger.info(f"PostAnalyzer initialized")
				
		except Exception as e:
			logger.error(f"Error during initialization: {e}")
			self.cleanup()
			sys.exit(1)

	def run(self):
		"""Run the posting loop"""
		self.running = True
		# Register signal handlers
		signal.signal(signal.SIGINT, self.handle_interrupt)
		signal.signal(signal.SIGTERM, self.handle_interrupt)
		
		# Wait before starting posting loop
		if self.agent_boot_wait_secs > 0:
			logger.info(f"Waiting {self.agent_boot_wait} minutes before starting posting...")
			time.sleep(self.agent_boot_wait_secs)
		
		try:
			# Main posting loop
			logger.info(f"Starting posting loop (interval: {self.post_interval} minutes)")
			while self.running:
				try:
					# Get context from past events
					self.context = Context()
					logger.info("Context loaded")

					if self.context.context_str != "": # Do not call the llm if recent context is empty
						# Create a commentary using context from monitor agent and notes of the post agents
						combined_context = self.context.context_str + self.context.notes
						analysis = self.post_analyzer.analyze_context(combined_context)
						image_path = self.context.save_post(analysis) # Save post to context/posts and get image path

						# Post to X/Twitter if conditions are satisfied
						if ( 
							self.x_enabled and 
							hasattr(self, 'x_client') and 
							analysis.get("post", False) and 
							analysis.get("commentary", False) and
							self.context.notes != "" # If the post agent has created a commentary with no notes, do not post to twitter.
						):
							success = self.x_client.post(analysis["commentary"], image_path)
							if success:
								logger.info(f"Posted to X/Twitter: {analysis['commentary'][:30]}...")
							else:
								logger.warning("Failed to post to X/Twitter")

						# Post agents updates it's notes
						new_notes = self.post_analyzer.update_notes(combined_context)
						if new_notes != "":
							self.context.save_notes(new_notes)

					# Wait until next posting check
					time.sleep(self.post_interval_secs)
				except Exception as e:
					logger.error(f"Error during posting cycle: {e}")
		finally:
			self.cleanup()

	def handle_interrupt(self, sig, frame):
		"""Handle keyboard interrupt or termination signal"""
		logger.info("Received interrupt signal, shutting down...")
		self.running = False
		raise KeyboardInterrupt

	def cleanup(self):
		"""Clean up resources"""
		logger.info("Cleaning up resources...")

if __name__ == "__main__":
	post_agent = PostAgent()
	post_agent.initialize()
	post_agent.run()