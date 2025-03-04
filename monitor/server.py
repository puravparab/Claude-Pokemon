import os
import logging
import threading
import http.server
import socketserver
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_PORT = 8001

class Server(threading.Thread):
	"""Run a simple HTTP server in a separate thread."""

	def __init__(self, port: int = DEFAULT_PORT, directory: str = "stream"):
		super().__init__(daemon=True)
		self.port = port
		self.directory = directory
		self.httpd: Optional[socketserver.TCPServer] = None
		
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
			self.httpd.server_close()
			logger.info("HTTP server stopped")