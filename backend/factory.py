from models.generator import GeneratorModel
from models.critic import CriticModel
from config import config

class ModelFactory:
    _instances: dict = {}

    @classmethod
    def get_generator(cls) -> GeneratorModel:
        if "generator" not in cls._instances:
            cls._instances["generator"] = GeneratorModel(
                api_key=config.GOOGLE_API_KEY,
                model_name="gemini-3-pro-image-preview"
            )
        return cls._instances["generator"]

    @classmethod
    def get_critic(cls) -> CriticModel:
        if "critic" not in cls._instances:
            cls._instances["critic"] = CriticModel(
                api_key=config.GOOGLE_API_KEY,
                model_name="gemini-3-flash-preview"
            )
        return cls._instances["critic"]

    @classmethod
    def get_adk_runner(cls, agent_yaml: str):
        from agent_loader import load_agent
        from google.adk.runners import InMemoryRunner
        return InMemoryRunner(agent=load_agent(agent_yaml), app_name="image_gen_app")
