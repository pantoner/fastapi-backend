# config.py
import os
from dotenv import load_dotenv

if not os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = "your_secret_key_here"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PROMPT_MICROSERVICE_URL = "https://profileprompt.onrender.com/build-prompt"


