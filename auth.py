import os
from dotenv import load_dotenv

load_dotenv()

API_USERNAME = os.environ.get('API_USERNAME')
API_PASSWORD = os.environ.get('API_PASSWORD')
API_URL = os.environ.get('API_URL')