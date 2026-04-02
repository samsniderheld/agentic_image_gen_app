pipeline = {
    "stage": "idle",
    "messages": [],       # list of message dicts sent to the frontend
    "context": {},        # shared flat dict flowing through agents
    "agents": [],         # list[AgentConfig] for the active pipeline
    "hitl_config": {},    # from build_hitl_config()
    "current_agent_index": 0,  # current position in the agents list
    "original_image_path": None,
    "current_image_path": None,
    "critique": None,
}

def reset():
    pipeline.update({
        "stage": "idle",
        "messages": [],
        "context": {},
        "agents": [],
        "hitl_config": {},
        "current_agent_index": 0,
        "original_image_path": None,
        "current_image_path": None,
        "critique": None,
    })
