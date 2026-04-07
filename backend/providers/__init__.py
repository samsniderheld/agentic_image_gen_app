import importlib

def get_llm_provider(name: str):
    return importlib.import_module(f"providers.{name}")

def get_image_provider(name: str):
    return importlib.import_module(f"providers.{name}")

def get_critic_provider(name: str):
    return importlib.import_module(f"providers.{name}")

def get_video_provider(name: str):
    return importlib.import_module(f"providers.{name}")
