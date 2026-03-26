from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

class Config:
    GOOGLE_API_KEY: str = os.environ["GOOGLE_API_KEY"]
    OUTPUT_DIR: Path = Path("./outputs")

config = Config()
