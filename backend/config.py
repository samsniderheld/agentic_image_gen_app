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

    # Comma-separated list of agents in execution order
    # "generator" must appear somewhere for an image to be produced
    PIPELINE: list[str] = [
        a.strip()
        for a in os.getenv("PIPELINE", "planner,art_director,dop,generator,critic").split(",")
        if a.strip()
    ]

config = Config()
