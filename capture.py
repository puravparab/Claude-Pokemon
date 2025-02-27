import os
import time
import logging
import threading
import http.server
import socketserver
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_PORT = 8000
MAX_PORT_ATTEMPTS = 100
EMBED_LOAD_TIMEOUT = 30
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

class Server(threading.Thread):
	"""Run a simple HTTP server in a separate thread."""
	def __init__(self, port: int = DEFAULT_PORT, directory: str = "output/stream"):
		super().__init__(daemon=True)
		self.port = port
		self.directory = directory
		self.httpd = None
		
	def run(self) -> None:
		"""Start the HTTP server."""
		os.makedirs(self.directory, exist_ok=True)
		handler = self._create_handler()
		self._try_start_server(self.port, handler)
	
	def _create_handler(self):
		"""Create HTTP handler with directory configuration."""
		return lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(
			*args, directory=self.directory, **kwargs
		)
	
	def _try_start_server(self, port: int, handler) -> bool:
		"""Try to start server on specified port."""
		try:
			self.port = port
			self.httpd = socketserver.TCPServer(("", port), handler)
			logger.info(f"HTTP server started on port {port}")
			self.httpd.serve_forever()
			return True
		except OSError:
			logger.warning(f"Port {port} is in use, trying next port")
			return False

	def stop(self):
		"""Stop the HTTP server."""
		if self.httpd:
			self.httpd.shutdown()
			logger.info("HTTP server stopped")

class TwitchCapture:
	# Move HTML template to class constant
	EMBED_HTML_TEMPLATE = """
		<!DOCTYPE html>
		<html>
		<head>
				<title>Twitch Stream Capture</title>
				<style>
						body, html {
								margin: 0;
								padding: 0;
								width: 100%%;
								height: 100%%;
								overflow: hidden;
								background-color: #000;
						}
						iframe {
								width: %(width)dpx;
								height: %(height)dpx;
								border: none;
						}
				</style>
		</head>
		<body>
				<iframe
						src="https://player.twitch.tv/?channel=%(channel)s&parent=localhost&muted=true"
						frameborder="0"
						allowfullscreen="true"
						scrolling="no"
						width="%(width)d"
						height="%(height)d">
				</iframe>
		</body>
		</html>
	"""

	def __init__(self, channel_name: str, images_dir: str = "images"):
		self.channel_name = channel_name
		self.images_dir = images_dir
		self.driver: Optional[webdriver.Chrome] = None
		
		self._setup_directories()
		self._setup_server()
		self.embed_file = self._create_embed_html()
		self.embed_url = f"http://localhost:{self.server.port}/twitch_embed.html"

	def _setup_directories(self) -> None:
		"""Create necessary directories."""
		os.makedirs(self.images_dir, exist_ok=True)
		os.makedirs("output/stream", exist_ok=True)

	def _setup_server(self) -> None:
		"""Initialize and start the HTTP server."""
		self.server = Server()
		self.server.start()
		time.sleep(1)  # Give the server a moment to start

	def _create_embed_html(self) -> str:
		"""Create an HTML file with the Twitch embed."""
		embed_html = self.EMBED_HTML_TEMPLATE % {
			'channel': self.channel_name,
			'width': WINDOW_WIDTH,
			'height': WINDOW_HEIGHT
		}

		file_path = os.path.join("output/stream", "twitch_embed.html")
		with open(file_path, "w") as f:
			f.write(embed_html)
		return file_path

	def init_driver(self) -> None:
		"""Set up the Selenium WebDriver for browser automation."""
		if self.driver:
			return
			
		options = Options()
		options.add_argument("--headless=new")
		# Performance optimizations
		options.add_argument("--disable-gpu")
		options.add_argument("--disable-dev-shm-usage")
		options.add_argument("--no-sandbox")
		options.add_argument("--disable-extensions")
		options.add_argument("--disable-infobars")
		# Reduce memory usage
		options.add_argument("--js-flags=--expose-gc")
		options.add_argument("--disable-web-security")
		options.add_argument("--disable-features=IsolateOrigins,site-per-process")
		# Media stream handling for Twitch
		options.add_argument("--autoplay-policy=no-user-gesture-required")
		options.add_argument("--use-fake-ui-for-media-stream")
		# Window size must still be set even in headless mode
		options.add_argument(f"--window-size={WINDOW_WIDTH},{WINDOW_HEIGHT}")
		# Add experimental options
		options.add_experimental_option("excludeSwitches", ["enable-automation"])
		options.add_experimental_option("useAutomationExtension", False)
		
		self.driver = webdriver.Chrome(options=options)
		logger.info("Initialized Chrome WebDriver")

	def capture_screenshot(self) -> str:
		"""Navigate to Twitch embed and capture a screenshot."""
		try:
			self.init_driver()
			timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_UTC")
			filename = f"{self.images_dir}/{timestamp}.png"
			
			logger.info(f"Loading Twitch embed via HTTP: {self.embed_url}")
			self.driver.get(self.embed_url)
			
			self._wait_for_embed_loading()
			self.driver.save_screenshot(filename)
			logger.info(f"Screenshot saved to {filename}")
			
			return filename
			
		except Exception as e:
			logger.error(f"Error capturing screenshot: {e}")
			raise

	def _wait_for_embed_loading(self) -> None:
		"""Wait for the embed to load completely."""
		try:
			# wait for iframe
			WebDriverWait(self.driver, EMBED_LOAD_TIMEOUT).until(
				EC.presence_of_element_located((By.TAG_NAME, "iframe"))
			)
			time.sleep(10)
		except Exception as e:
			logger.warning(f"Timeout waiting for embed to load: {e}")

	def cleanup(self):
		"""Close browser and clean up resources."""
		if self.driver:
			self.driver.quit()
			self.driver = None
			logger.info("WebDriver session closed")

		# Stop the HTTP server
		if hasattr(self, 'server'):
			self.server.stop()
