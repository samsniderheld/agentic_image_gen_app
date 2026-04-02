from dataclasses import dataclass, field
from pathlib import Path
import yaml
import os

AGENTS_DIR = Path(__file__).parent / "agents"
CONFIG_DIR = Path(__file__).parent / "config"

@dataclass
class AgentConfig:
    name: str
    display_name: str
    type: str            # llm_agent | generator_agent | critic_agent
    instruction: str
    model_provider: str  # routes to providers/<name>.py
    model_name: str
    temperature: float
    max_tokens: int
    inputs: list = field(default_factory=list)
    outputs: list = field(default_factory=list)
    hitl: dict = field(default_factory=dict)

def load_agent(name: str) -> AgentConfig:
    raw = yaml.safe_load((AGENTS_DIR / f"{name}.yaml").read_text())
    model = raw.get("model", {})
    return AgentConfig(
        name=raw["name"],
        display_name=raw.get("display_name", name),
        type=raw["type"],
        instruction=raw.get("instruction", ""),
        model_provider=model.get("provider", "gemini"),
        model_name=model.get("name", "gemini-2.5-pro-preview-03-25"),
        temperature=model.get("temperature", 0.7),
        max_tokens=model.get("max_tokens", 2048),
        inputs=raw.get("inputs", []),
        outputs=raw.get("outputs", []),
        hitl=raw.get("hitl", {}),
    )

def load_pipeline(name: str = None) -> list:
    raw = yaml.safe_load((CONFIG_DIR / "pipeline.yaml").read_text())
    name = name or os.getenv("PIPELINE", raw["active_pipeline"])
    return [load_agent(n) for n in raw["pipelines"][name]["agents"]]

def build_hitl_config(pipeline: list) -> dict:
    """
    Keyed by agent name. Contains only what the action handler needs to build
    review UI messages. next_agent/next_stage are not here — derived at runtime
    from pipeline list position.
    """
    result = {}
    for cfg in pipeline:
        h = cfg.hitl
        if not h.get("enabled"):
            continue
        result[cfg.name] = {
            "output_field": cfg.outputs[0]["target"] if cfg.outputs else None,
            "output_label": h.get("output_label", "Output"),
            "thinking_revise": h.get("thinking_revise_message", "Revising..."),
            "approval_message": h.get("approval_message", "Approved."),
            "approve_label": h.get("approve_label", "✓ Approve"),
            "feedback_target": h.get("feedback_target"),
        }
    return result
