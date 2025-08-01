import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
FOLDER_OUTPUT = os.getenv("FOLDER_OUTPUT")
BOT_TOKEN = os.getenv("BOT_TOKEN")