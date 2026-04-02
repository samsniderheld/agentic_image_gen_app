# Agentic Pipeline Framework

A lightweight framework for rapidly assembling and running agentic pipelines. Agents are defined in YAML, pipelines are composed in a config file, and AI providers are swappable modules.

## Framework Concept

The core idea is that most agentic workflows follow the same pattern: a sequence of AI-powered steps, each reading from shared context, producing output back into that context, optionally pausing for human review before continuing. The framework makes this pattern fully configurable without writing Python for each new pipeline.

### What the framework provides:

- A universal agent runner that works for any agent type
- A YAML schema for defining agents (inputs, outputs, model, HITL settings)
- A pipeline config for composing agents into ordered sequences
- A swappable provider system for routing AI calls to any backend
- A single-endpoint HTTP API that drives the pipeline from a frontend
- A chat-based frontend with a typed message/bubble system for building review UIs

### Starter Pipeline

The framework ships with a starter pipeline for **conversational image generation** to demonstrate all framework capabilities:

1. **Planner** — expands user prompt into detailed creative brief (with HITL review)
2. **Art Director** — adds visual style specifications (with HITL review)
3. **Director of Photography** — defines camera and shot details (with HITL review)
4. **Generator** — creates the image from combined prompts
5. **Critic** — analyzes image quality and suggests improvements
6. Optional fix application via inpainting with before/after comparison

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Google AI API key (for Gemini provider)

### Installation

1. Clone the repository
2. Copy `.env.example` to `.env` and add your API key:
   ```bash
   cp .env.example .env
   # Edit .env and add your GOOGLE_API_KEY
   ```

3. Install dependencies:
   ```bash
   # Backend
   cd backend
   pip install -r requirements.txt
   cd ..

   # Frontend
   cd frontend
   npm install
   cd ..
   ```

4. Start the application:
   ```bash
   ./start.sh
   ```

5. Open your browser to `http://localhost:5001`

## Project Structure

```
backend/
  providers/          # AI provider implementations
    gemini.py         # Gemini: LLM + image generation + vision critique
    openai.py         # OpenAI: placeholder stub
    __init__.py       # Provider dispatcher
  agents/             # Agent YAML definitions
    planner.yaml
    art_director.yaml
    dop.yaml
    generator.yaml
    critic.yaml
  config/
    pipeline.yaml     # Pipeline configurations
  loader.py           # YAML → AgentConfig dataclasses
  runner.py           # Universal agent runner
  state.py            # Global pipeline state
  app.py              # Flask API server
  requirements.txt

frontend/
  src/
    bubbles/          # UI components for different message types
    chat/             # Chat UI components
    App.jsx           # Main application component
    api.js            # API communication layer
    styles.css        # Dark theme styling
  package.json
  vite.config.js

start.sh              # Startup script
.env.example          # Environment template
```

## Framework Architecture

### Core Abstractions

**Agent** — A single step in a pipeline, defined entirely in YAML:
- Has typed inputs (read from context)
- Has typed outputs (written back to context)
- Uses a model/provider configuration
- Optional HITL (human-in-the-loop) settings

**Pipeline Context** — A Python dict that flows through the entire pipeline:
- Each agent reads the keys it needs
- Writes its result to a new key
- Passes the dict to the next agent

**Pipeline** — An ordered list of agent names in `pipeline.yaml`:
- Multiple named pipelines can coexist
- The active one is selected by config or env var
- The runner advances through the list, pausing at HITL gates

**Provider** — A Python module implementing AI capabilities:
- Three capability roles: LLM, image generation, vision critique
- Any provider can implement any subset of roles
- Switching providers is a one-line YAML change

**Action Endpoint** — A single `POST /api/action` route handles all interactions:
- The backend tracks pipeline state via `current_agent_index`
- The frontend just sends decisions and data

### Agent YAML Schema

```yaml
name: string                    # unique identifier
display_name: string            # shown in UI
type: llm_agent                 # llm_agent | generator_agent | critic_agent

model:
  provider: gemini              # routes to providers/<name>.py
  name: string                  # model name
  temperature: float            # llm_agent only
  max_tokens: int               # llm_agent only

instruction: |                  # system prompt — llm_agent only
  ...

inputs:
  - name: string                # parameter name
    source: string              # context dict key to read from
    fallback: string            # fallback context key if source is None
    optional: bool              # if true, None is acceptable
    default: any                # used when source and fallback are both None
    combine_with: [key, key]    # join source with these keys
    separator: string           # separator for combine_with

outputs:
  - name: string
    target: string              # context dict key to write to
    save_to_disk: string        # if set, PIL.Image is saved here

hitl:
  enabled: bool
  review_stage: string          # stage name for this review gate
  output_label: string          # label shown above output
  thinking_message: string      # shown while agent is running
  thinking_revise_message: string  # shown while re-running after feedback
  approve_label: string         # approve button label
  feedback_target: string       # context key for user feedback
  approval_message: string      # message on approval
```

### Pipeline Configuration

```yaml
# backend/config/pipeline.yaml
active_pipeline: default

pipelines:
  default:
    agents: [planner, art_director, dop, generator, critic]

  quick:
    agents: [planner, generator, critic]

  minimal:
    agents: [generator, critic]
```

Select a pipeline by setting `PIPELINE=quick` in `.env`.

## Building a New Pipeline

To create a new pipeline or modify the existing one:

1. **Define agents** — Create YAML files in `backend/agents/`
2. **Register the pipeline** — Add a named entry to `backend/config/pipeline.yaml`
3. **Add provider functions** — If new capabilities are needed, add them to provider modules
4. **Add message types** — If new UI interactions are needed, add bubble components
5. **Activate** — Set `active_pipeline` in `pipeline.yaml` or `PIPELINE=` in `.env`

No changes to the core framework code are needed for steps 1-2.

## Extensibility Reference

| Task | What to change |
|------|----------------|
| Add an agent to a pipeline | Create `agents/<name>.yaml`, add name to `pipeline.yaml` |
| Change an agent's instruction | Edit `instruction:` in its YAML |
| Change the model for any agent | Edit `model.name:` in its YAML |
| Switch any agent to a different provider | Edit `model.provider:` in its YAML |
| Add a new AI provider | Create `providers/<name>.py`, implement needed role functions |
| Add a new agent type | Add case to `PROVIDER_DISPATCH` in `runner.py` |
| Create an alternative pipeline | Add entry under `pipelines:` in `pipeline.yaml` |
| Add a new UI interaction | Add message type to `app.py`, add bubble component |

## Provider Interface

Providers implement capability roles by exposing specific function signatures:

### LLM Role
```python
def call_llm(instruction: str, user_message: str, model_name: str,
             temperature: float, max_tokens: int) -> str
```

### Image Generation Role
```python
def generate_image(prompt: str, aspect_ratio: str, model_name: str,
                   input_images: list | None = None) -> PIL.Image

def inpaint_image(image: PIL.Image, fix_prompts: list[str],
                  aspect_ratio: str, model_name: str) -> PIL.Image
```

### Vision Critic Role
```python
def critique_image(image: PIL.Image, original_prompt: str) -> dict
# Returns:
# {
#   "overall_score": float (0.0–1.0),
#   "overall_assessment": str,
#   "fixes_required": [
#     {
#       "fix_id": str,
#       "severity": "low" | "medium" | "high",
#       "issue_description": str,
#       "fix_prompt": str
#     }
#   ],
#   "pass_threshold_met": bool  # True if score >= 0.8
# }
```

## API Reference

### POST /api/action

Single endpoint for all pipeline interactions.

**Request:**
```json
{
  "action": "generate",
  "prompt": "a sunset over mountains",
  "aspect_ratio": "16:9",
  "images": ["<base64>"]
}
```

**Response:**
```json
{
  "messages": [
    {"type": "text", "role": "agent", "text": "..."},
    {"type": "thinking", "text": "Planning your prompt..."},
    {"type": "image", "src": "/outputs/image.png", "caption": "..."}
  ]
}
```

**Actions:**
- `generate` — Start a new pipeline run
- `review` — Handle HITL review decision (approve/feedback/reject)
- `critique` — Run the critic agent
- `apply_fixes` — Apply selected fixes via inpainting
- `accept_fix` — Accept/reject/re-critique after fixes

## Message Types

The frontend renders different bubble components based on message type:

| Type | Component | Use |
|------|-----------|-----|
| `text` | TextBubble | Plain text messages |
| `thinking` | ThinkingBubble | Collapsible status indicator |
| `image` | ImageBubble | Image with caption, click to enlarge |
| `comparison` | ComparisonBubble | Before/after side by side |
| `options` | OptionsBubble | Action buttons with optional feedback |
| `checklist` | ChecklistBubble | Fix list with severity and custom fixes |
| `critique` | CritiqueBubble | Score bar, pass/fail badge, assessment |
| `final` | FinalBubble | Final image with download and restart |

## Development

### Backend Development

```bash
cd backend
python app.py
```

The backend runs on `http://localhost:5001`.

### Frontend Development

```bash
cd frontend
npm run dev
```

The frontend dev server runs on `http://localhost:5173` and proxies API calls to the backend.

### Testing a New Agent

1. Create `backend/agents/my_agent.yaml`
2. Add it to a pipeline in `backend/config/pipeline.yaml`
3. Restart the backend
4. The agent will automatically run in the pipeline sequence

## Environment Variables

```bash
GOOGLE_API_KEY=       # Required for Gemini provider
OPENAI_API_KEY=       # Optional, for OpenAI provider
PIPELINE=default      # Override active pipeline
```

## License

MIT

## Contributing

Contributions are welcome! The framework is designed to be extended:

- Add new providers in `backend/providers/`
- Add new agents in `backend/agents/`
- Add new bubble components in `frontend/src/bubbles/`
- Create new pipelines in `backend/config/pipeline.yaml`

The core framework files (`loader.py`, `runner.py`, `state.py`, `app.py`) should rarely need modification.
