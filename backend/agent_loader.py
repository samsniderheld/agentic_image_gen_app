import yaml
from pathlib import Path
from google.adk.agents import LlmAgent, SequentialAgent, LoopAgent
from pipeline.tools import get_tool

AGENTS_DIR = Path(__file__).parent / "agents"

def load_agent(name: str):
    path = AGENTS_DIR / f"{name}.yaml"
    with open(path) as f:
        spec = yaml.safe_load(f)
    return _build(spec)

def _build(spec: dict):
    t = spec["type"]

    if t == "llm":
        return LlmAgent(
            name=spec["name"],
            model=spec.get("model", "gemini-2.0-flash"),
            description=spec.get("description", ""),
            instruction=spec.get("instruction", ""),
            output_key=spec.get("output_key"),
            tools=[get_tool(n) for n in spec.get("tools", [])],
            include_contents=spec.get("include_contents", "none"),
        )

    sub_agents = [_build(s) if isinstance(s, dict) else load_agent(s)
                  for s in spec.get("sub_agents", [])]

    if t == "sequential":
        return SequentialAgent(
            name=spec["name"],
            description=spec.get("description", ""),
            sub_agents=sub_agents,
        )

    if t == "loop":
        return LoopAgent(
            name=spec["name"],
            description=spec.get("description", ""),
            sub_agents=sub_agents,
            max_iterations=spec.get("max_iterations", 3),
        )

    raise ValueError(f"Unknown agent type: {t}")
