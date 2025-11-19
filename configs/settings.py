# configs/settings.py
import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("MODEL", "gpt-4o-mini")
S2_API_KEY = os.getenv("S2_API_KEY")
PAPER_PROVIDER = os.getenv("PAPER_PROVIDER", "s2")
GITHUB_API_TOKEN: str | None = os.getenv("GITHUB_API_TOKEN")