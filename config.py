from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in .env")
if not SERPER_API_KEY:
    raise RuntimeError("SERPER_API_KEY not found in .env")

client = OpenAI(api_key=OPENAI_API_KEY)