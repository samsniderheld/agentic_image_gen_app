from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

class Config:
    GOOGLE_API_KEY: str = os.environ["GOOGLE_API_KEY"]
    OUTPUT_DIR: Path = Path("./outputs")

    # Backend selection (change via env vars to swap implementations)
    GENERATOR_BACKEND: str = os.getenv("GENERATOR_BACKEND", "gemini")
    CRITIC_BACKEND: str = os.getenv("CRITIC_BACKEND", "gemini")

config = Config()
