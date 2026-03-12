import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

EMBEDDING_MODEL = "gemini-embedding-2-preview"
EMBEDDING_DIM = 1536
LLM_MODEL = "gemini-3.1-flash-lite-preview"
