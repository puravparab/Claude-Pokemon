import os
import logging
import tweepy
from typing import Optional

logger = logging.getLogger(__name__)

class TwitterPoster:
	"""Posts text and images to Twitter/X.com using Twitter API v2 with v1.1 for media upload"""

	def __init__(self, api_key: str, api_secret: str, access_token: str, access_secret: str):
		"""Initialize with Twitter API credentials"""
		self.api_key = api_key
		self.api_secret = api_secret
		self.access_token = access_token
		self.access_secret = access_secret
		self.client_v2 = None
		self.api_v1_upload = None
		self._authenticate()
		
	def _authenticate(self) -> None:
		"""Authenticate with Twitter API v2 and v1.1 for media upload only"""
		try:
			# Authenticate with v2 API for posting
			self.client_v2 = tweepy.Client(
				consumer_key=self.api_key,
				consumer_secret=self.api_secret,
				access_token=self.access_token,
				access_token_secret=self.access_secret
			)
			logger.info("Successfully initialized Twitter API v2 client")
			
			# Authenticate with v1.1 API for media upload only
			auth = tweepy.OAuth1UserHandler(
				self.api_key, 
				self.api_secret,
				self.access_token,
				self.access_secret
			)
			self.api_v1_upload = tweepy.API(auth)
			logger.info("Successfully initialized Twitter API v1.1 for media upload")
				
		except Exception as e:
			logger.error(f"Twitter authentication failed: {e}")
			self.client_v2 = None
			self.api_v1_upload = None
				
	def post_with_image(self, text: str, image_path: str) -> bool:
		"""Post a tweet with text and image"""
		if not self.client_v2 or not self.api_v1_upload:
			logger.error("Cannot post to Twitter: not authenticated")
			return False
			
		if not os.path.exists(image_path):
			logger.error(f"Image file not found: {image_path}")
			return False
				
		try:
			# Upload media using v1.1 API
			media = self.api_v1_upload.media_upload(image_path)
			media_id = media.media_id_string
			logger.info(f"Successfully uploaded media with ID: {media_id}")
			
			# Post tweet with media using v2 API
			response = self.client_v2.create_tweet(
				text=text,
				media_ids=[media_id]
			)
			tweet_id = response.data['id']
			logger.info(f"Successfully posted to Twitter with image: {text[:30]}... (Tweet ID: {tweet_id})")
			return True
				
		except tweepy.errors.Forbidden as e:
			logger.error(f"403 Forbidden error: Your account doesn't have permission to post. "
										f"Twitter API now requires a paid subscription for posting. Error: {e}")
			return False
		except Exception as e:
			logger.error(f"Error posting to Twitter: {e}")
			return False