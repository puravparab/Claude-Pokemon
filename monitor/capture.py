import os
import time
import logging
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Optional

logger = logging.getLogger(__name__)

WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1200
EMBED_LOAD_TIMEOUT = 20

# Chrome configuration options
CHROME_CONFIG = {
	"arguments": [
		"--headless=new",
		# Performance optimizations
		"--disable-gpu",
		"--disable-dev-shm-usage",
		"--no-sandbox",
		"--disable-extensions",
		"--disable-infobars",
		# Reduce memory usage
		"--js-flags=--expose-gc",
		"--disable-web-security",
		"--disable-features=IsolateOrigins,site-per-process",
		# Media stream handling for Twitch
		"--autoplay-policy=no-user-gesture-required",
		"--use-fake-ui-for-media-stream",
	],
	"experimental_options": {
		"excludeSwitches": ["enable-automation"],
		"useAutomationExtension": False
	}
}

class TwitchCapture:
	def __init__(
		self, 
		server_port: int, 
		images_dir: str = "context/images"
	):
		self.images_dir = images_dir
		self.server_port = server_port
		self.driver: Optional[webdriver.Chrome] = None
		self.embed_url = f"http://localhost:{self.server_port}/twitch.html"
		
		# Create images directory if it does not exist
		os.makedirs(self.images_dir, exist_ok=True)

	def init(self) -> None:
		"""Set up the Selenium WebDriver for browser automation."""
		if self.driver:
			return
		# Add options
		options = Options()
		for option in CHROME_CONFIG["arguments"]:
			options.add_argument(option)
		options.add_argument(f"--window-size={WINDOW_WIDTH},{WINDOW_HEIGHT}")
		# Add experimental options
		for key, value in CHROME_CONFIG["experimental_options"].items():
			options.add_experimental_option(key, value)
		
		self.driver = webdriver.Chrome(options=options)
		logger.info("Initialized Chrome WebDriver")
		
		# Load the embed page once
		self._load_embed_page()

	def _load_embed_page(self) -> None:
		"""Load the Twitch embed page once and wait for it to initialize."""
		try:
			logger.info(f"Loading Twitch embed via HTTP: {self.embed_url}")
			self.driver.get(self.embed_url)
			self._wait_for_embed_loading()
			logger.info("Twitch embed loaded successfully")
		except Exception as e:
			logger.error(f"Error loading Twitch embed: {e}")
			raise

	def _wait_for_embed_loading(self) -> None:
		"""Wait for the embed to load completely."""
		try:
			# wait for iframe
			WebDriverWait(self.driver, EMBED_LOAD_TIMEOUT).until(
				EC.presence_of_element_located((By.TAG_NAME, "iframe"))
			)
			time.sleep(10) # DO NOT remove or screenshots will be obstructed by other elements
		except Exception as e:
			logger.warning(f"Timeout waiting for embed to load: {e}")

	def capture_screenshot(self) -> str:
		"""Capture a screenshot of the twitch stream."""
		try:
			# Make sure we have a driver
			if not self.driver:
				self.init()
					
			timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_UTC")
			filename = f"{self.images_dir}/{timestamp}.png"
			self.driver.save_screenshot(filename)
			logger.info(f"Screenshot saved to {filename}")
			return filename
				
		except Exception as e:
			logger.error(f"Error capturing screenshot: {e}")
			raise

	def cleanup(self):
		"""Close browser and clean up resources."""
		if self.driver:
			self.driver.quit()
			self.driver = None
			logger.info("WebDriver session closed")