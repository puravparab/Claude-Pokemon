import os
import logging
import tweepy
from typing import Optional

logger = logging.getLogger(__name__)

class TwitterClient:
	"""Posts text and images to Twitter/X"""
	def __init__(
		self, 
		api_key: str,
		api_secret: str, 
		access_token: str, 
		access_secret: str
	):
		"""Initialize with Twitter API credentials"""
		self.api_key = api_key
		self.api_secret = api_secret
		self.access_token = access_token
		self.access_secret = access_secret

		# Authenticate with Twitter API
		try:
			# Set up v2 client for posting
			self.client_v2 = tweepy.Client(
				consumer_key=api_key,
				consumer_secret=api_secret,
				access_token=access_token,
				access_token_secret=access_secret
			)
			# Set up v1.1 API for media upload
			auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
			self.api_v1 = tweepy.API(auth)
			logger.info("Twitter API initialized successfully")
		except Exception as e:
			logger.error(f"Twitter API initialization failed: {e}")
			self.client_v2 = None
			self.api_v1 = None
		
	def post(self, text: str, image_path: str = "") -> bool:
		"""Post to Twitter with/without an image"""
		if not self.client_v2 or not self.api_v1:
			logger.error("Twitter API not initialized")
			return False

		try:
			# If image path is provided and valid, upload and include it
			media_ids = []
			if image_path and os.path.exists(image_path):
				media = self.api_v1.media_upload(image_path)
				media_ids.append(media.media_id_string)
				logger.info(f"Uploaded image: {image_path}")
			
			# Create the tweet
			response = self.client_v2.create_tweet(text=text, media_ids=media_ids if media_ids else None)
			logger.info(f"Tweet posted successfully")
			return True
			
		except Exception as e:
			logger.error(f"Failed to post to Twitter: {e}")
			return False