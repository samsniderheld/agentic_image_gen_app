# Architecture & Data Flow

This document provides detailed architecture diagrams and data flow explanations for the Agentic Image Generation Pipeline.

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [State Management](#state-management)
5. [Message Flow](#message-flow)
6. [API Request/Response Cycle](#api-requestresponse-cycle)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER (Browser)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FLASK SERVER :8000                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              React Frontend (Static Files)                │  │
│  │  - Chat UI with message bubbles                           │  │
│  │  - HITL review UI with feedback input                     │  │
│  │  - Stage-based routing logic                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             │ /api/* requests                    │
│                             ▼                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   Flask API Routes                        │  │
│  │  - /api/generate                                          │  │
│  │  - /api/review/agent (generic HITL gate)                 │  │
│  │  - /api/critique (unified initial + re-critique)          │  │
│  │  - /api/review/fixes                                      │  │
│  │  - /api/fix/accept                                        │  │
│  │  - AGENT_CONFIG: drives all review workflows             │  │
│  └─────────────┬─────────────────────────────────────────────┘  │
│                │                                                 │
│                ▼                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   Global State                            │  │
│  │  - pipeline: {stage, current_image_path,                 │  │
│  │              original_image_path, messages,               │  │
│  │              pipeline_context, ...}                       │  │
│  │  - PipelineContext flows between agents                  │  │
│  └─────────────┬─────────────────────────────────────────────┘  │
│                │                                                 │
│                ▼                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              ABC-Based Agent Pipeline                     │  │
│  │  - Planner: Prompt enrichment                             │  │
│  │  - Art Director: Style definition                         │  │
│  │  - DOP: Shot specification                                │  │
│  │  - Generator: Image generation (wrapper)                  │  │
│  │  - Critic: Vision critique (wrapper)                      │  │
│  └─────────────┬─────────────────────────────────────────────┘  │
│                │                                                 │
│                ▼                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Model Registry & Backends                    │  │
│  │  - GeminiGenerator (gemini-3-pro-image-preview)           │  │
│  │  - GeminiCritic (gemini-3.1-pro-preview)                  │  │
│  │  - Lazy loading to avoid circular imports                │  │
│  └─────────────┬─────────────────────────────────────────────┘  │
│                │                                                 │
└────────────────┼─────────────────────────────────────────────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │   Google Gemini API    │
    │  - Image Generation    │
    │  - Vision Critique     │
    │  - LLM for Agents      │
    └────────────────────────┘
```

---

## Component Architecture

### Backend Components

```
backend/
│
├── app.py ──────────────► Flask Routes + Request Handling
│                          │
│                          ├─► /api/generate (starts planner)
│                          ├─► /api/review/agent (generic HITL gate)
│                          ├─► /api/critique (initial + re-critique)
│                          ├─► /api/review/fixes
│                          ├─► /api/fix/accept
│                          └─► AGENT_CONFIG (configuration dictionary)
│
├── state.py ────────────► Global State Management
│                          │
│                          ├─► pipeline: dict (stage, messages, etc.)
│                          ├─► pipeline_context: PipelineContext
│                          └─► push_message()
│
├── agent.py ────────────► Pipeline Runner Functions
│                          │
│                          ├─► get_pipeline() → builds agent pipeline
│                          ├─► run_pre_generation(ctx) → planner/art_director/dop
│                          ├─► run_generator(ctx) → generator
│                          └─► run_post_generation(ctx) → critic
│
├── config.py ───────────► Configuration
│                          │
│                          └─► PIPELINE = ["planner", "art_director", "dop",
│                                         "generator", "critic"]
│
├── models/
│   ├── base.py ─────────► ABC Definitions
│   │                      │
│   │                      ├─► ImageGenerator (ABC)
│   │                      ├─► ImageCritic (ABC)
│   │                      └─► PipelineAgent (ABC)
│   │
│   ├── registry.py ─────► Registration & Factory
│   │                      │
│   │                      ├─► get_generator() → GeminiGenerator
│   │                      ├─► get_critic() → GeminiCritic
│   │                      └─► build_pipeline() → [PipelineAgent]
│   │
│   ├── pipeline_context.py ──► PipelineContext dataclass
│   │
│   ├── generators/
│   │   └── gemini.py ───► GeminiGenerator (generation + inpainting)
│   │
│   └── critics/
│       └── gemini.py ───► GeminiCritic (critique + prompt inference)
│
├── pipeline/
│   └── tools.py ────────► Fix Application Tool
│                          │
│                          └─► apply_all_fixes() [full-image inpainting]
│
├── agents/
│   ├── planner_agent.py ────────► Prompt enrichment
│   ├── art_director_agent.py ───► Style definition
│   ├── dop_agent.py ────────────► Shot specification
│   ├── generator_agent.py ──────► Image generation wrapper
│   └── critic_agent.py ─────────► Critique wrapper
│
└── schemas.py ──────────► Pydantic Models
                           │
                           ├─► GenerationRequest
                           ├─► CritiqueResult
                           └─► Fix
```

### Frontend Components

```
frontend/src/
│
├── App.jsx ─────────────► Main Application
│                          │
│                          ├─► Message state management
│                          ├─► Stage-based routing (awaiting_*_review)
│                          ├─► handleOption (approve/feedback/reject)
│                          ├─► handleChecklist (fix selection)
│                          └─► handleRecritique
│
├── api.js ──────────────► API Client
│                          │
│                          ├─► generate(form)
│                          ├─► reviewAgent(agent, decision, feedback)
│                          ├─► critique(isRecritique)
│                          ├─► reviewFixes(ids, customFixes)
│                          └─► acceptFix(accepted)
│
├── chat/
│   ├── MessageList.jsx ─► Scrollable message container
│   ├── Message.jsx ─────► Message type router
│   └── InputBar.jsx ────► Text/image input
│
├── bubbles/
│   ├── TextBubble.jsx ──────────► Simple text
│   ├── ThinkingBubble.jsx ──────► Collapsible thinking
│   ├── ImageBubble.jsx ─────────► Image display
│   ├── ComparisonBubble.jsx ────► Before/after
│   ├── OptionsBubble.jsx ───────► Multiple choice + feedback input
│   ├── ChecklistBubble.jsx ─────► Fix selection + custom fixes
│   ├── CritiqueBubble.jsx ──────► Score display
│   ├── InputRequestBubble.jsx ──► Text input prompt
│   └── FinalBubble.jsx ─────────► Final with download
│
└── components/
    └── PromptForm.jsx ──► Initial generation form
```

---

## Data Flow Diagrams

### 1. Pre-Generation Pipeline (HITL Gates)

```
User submits prompt
    │
    ▼
POST /api/generate
    │
    ├─► Create PipelineContext(original_prompt=prompt, aspect_ratio=aspect_ratio)
    ├─► Update state.pipeline["stage"] = "running_planner"
    │
    ├─► Run Planner Agent
    │   ├─► planner.run(ctx) → enriches prompt
    │   └─► ctx.enriched_prompt = detailed brief
    │
    ├─► state.pipeline["pipeline_context"] = ctx
    ├─► Push message: enriched prompt
    ├─► Push message: options (approve/feedback/reject)
    └─► Return {stage: "awaiting_planner_review", messages: [...]}
        │
        ▼
User reviews enriched prompt → handleOption("approve") OR handleOption("feedback", "user input")
    │
    ▼
POST /api/review/agent {agent: "planner", decision: "approve"} OR {decision: "feedback", feedback: "..."}
    │
    ├─► Load ctx = state.pipeline["pipeline_context"]
    │
    ├─► If decision == "feedback":
    │   ├─► ctx.original_prompt += f"\n\nUser feedback: {feedback}"
    │   ├─► planner.run(ctx) → re-generates enriched prompt
    │   └─► Return to review
    │
    ├─► If decision == "approve":
    │   ├─► Run Art Director Agent
    │   │   ├─► art_director.run(ctx) → defines style
    │   │   └─► ctx.style_brief = style definition
    │   │
    │   ├─► Push message: style brief
    │   ├─► Push message: options (approve/feedback/reject)
    │   └─► Return {stage: "awaiting_art_director_review", messages: [...]}
    │       │
    │       ▼
User reviews style brief → handleOption("approve")
    │
    ▼
POST /api/review/agent {agent: "art_director", decision: "approve"}
    │
    ├─► Run DOP Agent
    │   ├─► dop.run(ctx) → defines shot
    │   └─► ctx.shot_brief = shot specifications
    │
    ├─► Push message: shot brief
    ├─► Push message: options (approve/feedback/reject)
    └─► Return {stage: "awaiting_dop_review", messages: [...]}
        │
        ▼
User reviews shot setup → handleOption("approve")
    │
    ▼
POST /api/review/agent {agent: "dop", decision: "approve"}
    │
    ├─► Run Generator Agent
    │   ├─► generator.run(ctx)
    │   ├─► Combines: enriched_prompt + style_brief + shot_brief
    │   ├─► Calls GeminiGenerator.generate(combined_prompt, aspect_ratio)
    │   └─► ctx.image = PIL Image
    │
    ├─► Save image: outputs/00_initial.png
    ├─► Push messages: image, options
    └─► Return {stage: "awaiting_initial_review", messages: [...]}
```

### 2. Critique Flow

```
User clicks "✓ Looks good — critique it"
    │
    ▼
handleOption("accept") → stage === "awaiting_initial_review"
    │
    ▼
POST /api/critique {is_recritique: false}
    │
    ├─► Load current_image_path from state.pipeline
    ├─► Create PipelineContext with image
    │
    ├─► Run Critic Agent
    │   ├─► critic.run(ctx)
    │   ├─► Calls GeminiCritic.critique(image, prompt)
    │   │   └─► Gemini API (gemini-3.1-pro-preview)
    │   │       └─► Returns CritiqueResult dict
    │   │
    │   └─► ctx.critiques.append(result)
    │
    ├─► Save copy: outputs/01_annotated.png
    ├─► Update state.pipeline["critique"] = result
    │
    ├─► Push messages:
    │   ├─► {type: "critique", score, assessment, passed}
    │   ├─► {type: "image", url: "/outputs/01_annotated.png"}
    │   └─► {type: "checklist", items: [...fixes], allowRecritique: true}
    │
    └─► Return {stage: "awaiting_fix_review", messages: [...]}
        │
        ▼
Frontend renders ChecklistBubble
    │
    ├─► AI fixes shown with severity tags
    ├─► "+ Add Custom Fix" button
    └─► "🔄 Run Critique Again" button
```

### 3. Fix Application Flow

```
User selects fixes + adds custom fixes
    │
    ▼
ChecklistBubble.submit()
    │
    │ {approved_fix_ids: [...], custom_fixes: [{id, label, severity}]}
    ▼
handleChecklist(ids, customFixes)
    │
    ▼
POST /api/review/fixes
    │
    ├─► Get AI fixes from state.pipeline["critique"]
    ├─► Build fix list:
    │   ├─► AI fixes with matching IDs
    │   └─► Custom fixes converted to Fix format
    │
    ├─► If no fixes selected:
    │   ├─► Save current_image_path → final.png
    │   └─► Return {stage: "done"}
    │
    ├─► Push message: {type: "thinking", content: "Applying fixes..."}
    │
    ├─► tools.apply_all_fixes(current_image_path, fixes_json)
    │   │
    │   ├─► Load image from current_image_path
    │   ├─► Build combined fix prompt (all fixes listed)
    │   ├─► ModelFactory.get_generator().inpaint()
    │   │   │
    │   │   └─► Gemini API with:
    │   │       ├─► original image
    │   │       ├─► full mask (edit entire image)
    │   │       ├─► fix instructions
    │   │       └─► aspect_ratio from state
    │   │
    │   └─► Save: outputs/fixes_applied.png
    │
    ├─► Update: current_image_path = "outputs/fixes_applied.png"
    │
    ├─► Push messages:
    │   ├─► {type: "comparison", leftUrl: "00_initial.png", rightUrl: "fixes_applied.png"}
    │   └─► {type: "options", options: [accept, reject, recritique]}
    │
    └─► Return {stage: "awaiting_fixes_review", messages: [...]}
        │
        ▼
Frontend renders comparison + options
```

### 4. Re-critique Flow

```
User clicks "🔄 Run Critique Again"
    │
    ▼
handleRecritique() or handleOption("recritique")
    │
    ▼
POST /api/recritique
    │
    ├─► Determine current image:
    │   ├─► Use fixed_image_path if exists
    │   └─► Otherwise use image_path
    │
    ├─► Update state.pipeline["image_path"] to current version
    │   └─► Ensures next fixes apply to latest image
    │
    ├─► Push messages:
    │   ├─► {type: "user", content: "Run critique again"}
    │   ├─► {type: "thinking", content: "Running critique..."}
    │   └─► {type: "image", url: current_image_url, caption: "Current image"}
    │
    ├─► agent.run_adk_segment("critique_agent", ...)
    │   └─► Same as initial critique flow
    │
    ├─► Update state.pipeline["critique"]
    │
    ├─► Push messages:
    │   ├─► {type: "critique", score, assessment, passed}
    │   ├─► {type: "image", url: "/outputs/01_annotated.png"}
    │   └─► {type: "checklist", items: [...new_fixes], allowRecritique: true}
    │
    └─► Return {stage: "awaiting_fix_review", messages: [...]}
        │
        ▼
Frontend renders new critique
    │
    └─► Can select new fixes and iterate
```

### 5. Custom Fix Flow

```
User clicks "+ Add Custom Fix"
    │
    ▼
ChecklistBubble shows form
    │
    ├─► User enters: "Make the sky more blue"
    ├─► Clicks "Add Fix"
    │
    ├─► addCustomFix()
    │   │
    │   ├─► Create: {id: "custom_0", label: "Make the sky more blue", severity: "medium"}
    │   ├─► Add to customFixes array
    │   └─► Auto-check in checklist
    │
    └─► Custom fix appears with "CUSTOM" tag
        │
        ▼
User clicks "Apply X Selected Fixes"
    │
    ├─► Custom fixes included in approved list
    │
    └─► Backend creates Fix:
        {
          fix_id: "custom_0",
          severity: "medium",
          issue_description: "Custom user-requested change",
          fix_prompt: "Make the sky more blue"
        }
```

---

## State Management

### Backend State (state.py)

```python
pipeline = {
    "stage": str,                # Current workflow stage
    "request": dict,             # GenerationRequest data
    "current_image_path": str,   # Path to current image (ALWAYS latest version)
    "original_image_path": str,  # Path to original generated image (for comparison)
    "input_images": [PIL.Image], # Input images for composition
    "aspect_ratio": str,         # Selected aspect ratio
    "critique": dict,            # CritiqueResult data
    "messages": [dict],          # Message queue for chat UI
    "pipeline_context": PipelineContext | None,  # Context object flowing through agents
}
```

**PipelineContext Structure:**
```python
@dataclass
class PipelineContext:
    original_prompt: str
    aspect_ratio: str = "1:1"
    enriched_prompt: str | None = None  # From planner
    style_brief: str | None = None      # From art_director
    shot_brief: str | None = None       # From dop
    image: PIL.Image | None = None      # From generator
    critiques: list[dict] = field(default_factory=list)  # From critic
    metadata: dict = field(default_factory=dict)
```

**Key Principles:**
- `pipeline_context` flows through all agents, accumulating outputs
- Each agent reads from and writes to specific fields in the context
- `current_image_path` is the **single source of truth** for file storage
- `original_image_path` never changes after generation (used for comparisons)
- When fixes are applied, `current_image_path` is updated to the new version

### State Transitions

```
selecting_aspect_ratio
    │
    ▼ User selects aspect ratio
idle
    │
    ▼ User submits generation form
running_planner
    │
    ▼ Planner agent completes
awaiting_planner_review
    │
    ├─► User approves ──────────► running_art_director ──► awaiting_art_director_review
    ├─► User gives feedback ────► running_planner (with feedback)
    └─► User rejects ───────────► idle

awaiting_art_director_review
    │
    ├─► User approves ──────────► running_dop ──► awaiting_dop_review
    ├─► User gives feedback ────► running_art_director (with feedback)
    └─► User rejects ───────────► idle

awaiting_dop_review
    │
    ├─► User approves ──────────► running_generator ──► awaiting_initial_review
    ├─► User gives feedback ────► running_dop (with feedback)
    └─► User rejects ───────────► idle

awaiting_initial_review
    │
    ├─► User clicks "critique" ─► critiquing ──► awaiting_fix_review
    └─► User clicks "reject" ───► idle

awaiting_fix_review
    │
    ├─► User applies fixes ──────► applying_fixes ──► awaiting_fixes_review
    └─► User clicks recritique ──► running_critique ──► awaiting_fix_review

awaiting_fixes_review
    │
    ├─► User accepts ────────────► done
    ├─► User rejects ────────────► done (with original)
    └─► User clicks recritique ──► running_critique ──► awaiting_fix_review

done
    │
    └─► User clicks "Start Over" ─► selecting_aspect_ratio
```

---

## Message Flow

### Message Structure

All messages in the `state.pipeline["messages"]` array follow this structure:

```javascript
{
  role: "user" | "agent",
  type: "text" | "thinking" | "image" | "comparison" | "options" | "checklist" | "critique" | "input_request" | "final",
  // ... type-specific fields
}
```

### Message Types & Fields

**Text:**
```javascript
{role: "agent", type: "text", content: "Done! Here's your image:"}
```

**Thinking:**
```javascript
{role: "agent", type: "thinking", content: "Generating image..."}
```

**Image:**
```javascript
{role: "agent", type: "image", url: "/outputs/00_initial.png", caption: ""}
```

**Comparison:**
```javascript
{role: "agent", type: "comparison", leftUrl: "/outputs/00_initial.png", rightUrl: "/outputs/fixes_applied.png", caption: "Applied 3 fixes"}
```

**Options:**
```javascript
{role: "agent", type: "options", prompt: "What would you like to do?", options: [{label: "✓ Accept", value: "accept"}, ...]}
```

**Checklist:**
```javascript
{role: "agent", type: "checklist", prompt: "Select fixes:", items: [{id: "fix_1", label: "Fix sky color", severity: "high", checked: true}, ...], action: "apply_fixes", allowRecritique: true}
```

**Critique:**
```javascript
{role: "agent", type: "critique", score: 7.5, assessment: "Good quality but...", passed: false}
```

**Input Request:**
```javascript
{role: "agent", type: "input_request", placeholder: "Enter your prompt...", action: "resubmit_prompt"}
```

**Final:**
```javascript
{role: "agent", type: "final", url: "/outputs/final.png", caption: "Your image is ready."}
```

### Message Rendering Pipeline

```
Backend: state.push_message(msg)
    │
    ▼
API Response: {messages: [...]}
    │
    ▼
Frontend: App.jsx receives messages
    │
    ▼
MessageList maps over messages
    │
    ▼
Message.jsx routes by type
    │
    ├─► type === "text" ────────► TextBubble
    ├─► type === "thinking" ────► ThinkingBubble
    ├─► type === "image" ───────► ImageBubble
    ├─► type === "comparison" ──► ComparisonBubble
    ├─► type === "options" ─────► OptionsBubble
    ├─► type === "checklist" ───► ChecklistBubble
    ├─► type === "critique" ────► CritiqueBubble
    ├─► type === "input_request" ► InputRequestBubble
    └─► type === "final" ───────► FinalBubble
```

---

## API Request/Response Cycle

### Example: Full Critique Cycle

#### 1. Generate Image

**Request:**
```http
POST /api/generate
Content-Type: application/json

{
  "prompt": "a serene mountain landscape",
  "aspect_ratio": "16:9",
  "seed": null,
  "input_images": []
}
```

**Response:**
```json
{
  "stage": "awaiting_initial_review",
  "messages": [
    {"role": "agent", "type": "thinking", "content": "Generating with prompt: \"a serene mountain landscape\" at 16:9..."},
    {"role": "agent", "type": "text", "content": "Done! Here's your initial generation:"},
    {"role": "agent", "type": "image", "url": "/outputs/00_initial.png", "caption": ""},
    {"role": "agent", "type": "options", "prompt": "What would you like to do?", "options": [...]}
  ]
}
```

#### 2. Accept & Critique

**Request:**
```http
POST /api/review/initial
Content-Type: application/json

{
  "decision": "accept"
}
```

**Response:**
```json
{
  "stage": "awaiting_fix_review",
  "critique": {
    "overall_score": 7.5,
    "overall_assessment": "Good composition but colors could be more vibrant",
    "pass_threshold_met": false,
    "fixes_required": [
      {
        "fix_id": "fix_1",
        "severity": "high",
        "issue_description": "Sky lacks depth and vibrancy",
        "fix_prompt": "Enhance sky with deeper blues and dramatic clouds"
      }
    ]
  },
  "messages": [
    {"role": "agent", "type": "critique", "score": 7.5, "assessment": "...", "passed": false},
    {"role": "agent", "type": "image", "url": "/outputs/01_annotated.png", "caption": "Current image"},
    {"role": "agent", "type": "checklist", "prompt": "Select which fixes to apply:", "items": [...], "allowRecritique": true}
  ]
}
```

#### 3. Apply Fixes (with Custom Fix)

**Request:**
```http
POST /api/review/fixes
Content-Type: application/json

{
  "approved_fix_ids": ["fix_1", "custom_0"],
  "custom_fixes": [
    {"id": "custom_0", "label": "Add a small cabin in the foreground", "severity": "medium"}
  ]
}
```

**Response:**
```json
{
  "stage": "awaiting_fixes_review",
  "messages": [
    {"role": "user", "type": "text", "content": "2 fix(es) selected."},
    {"role": "agent", "type": "thinking", "content": "Applying 2 fix(es) to the image..."},
    {"role": "agent", "type": "comparison", "leftUrl": "/outputs/00_initial.png", "rightUrl": "/outputs/fixes_applied.png", "caption": "Applied 2 fix(es)"},
    {"role": "agent", "type": "options", "prompt": "Accept these changes?", "options": [..., {label: "🔄 Run Critique Again", value: "recritique"}]}
  ]
}
```

#### 4. Re-critique

**Request:**
```http
POST /api/recritique
Content-Type: application/json

{}
```

**Response:**
```json
{
  "stage": "awaiting_fix_review",
  "critique": {
    "overall_score": 8.7,
    "overall_assessment": "Much improved! Sky is vibrant and cabin adds interest",
    "pass_threshold_met": true,
    "fixes_required": []
  },
  "messages": [
    {"role": "user", "type": "text", "content": "Run critique again."},
    {"role": "agent", "type": "thinking", "content": "Running vision critique on the current image..."},
    {"role": "agent", "type": "image", "url": "/outputs/fixes_applied.png", "caption": "Current image"},
    {"role": "agent", "type": "critique", "score": 8.7, "assessment": "...", "passed": true},
    {"role": "agent", "type": "image", "url": "/outputs/01_annotated.png", "caption": "Current image"},
    {"role": "agent", "type": "checklist", "prompt": "No issues found! You can finalize the image:", "items": [], "allowRecritique": true}
  ]
}
```

---

## Summary

This architecture provides:

1. **Clean Separation**: Backend handles state/logic, frontend handles UI
2. **ABC Pattern**: Extensible agent system with abstract base classes
3. **Registry Pattern**: Centralized registration for agents and models
4. **Pipeline Pattern**: Sequential agent execution with context passing
5. **Human-in-the-Loop (HITL)**: Review gates between each pre-generation agent with feedback loops
6. **Configuration-Driven**: Single AGENT_CONFIG dictionary drives all review workflows
7. **Message-Based UI**: Flexible chat interface that can render any message type
8. **Iterative Refinement**: Critique → Fix → Re-critique loop
9. **Extensibility**: Easy to add new agents, message types, and workflow stages
10. **Single-Server**: Simple deployment with Flask serving everything

### Key Architectural Patterns

**ABC + Registry Pattern:**
- All agents inherit from `PipelineAgent` ABC
- All generators inherit from `ImageGenerator` ABC
- All critics inherit from `ImageCritic` ABC
- Centralized registry in `models/registry.py` for easy swapping

**Pipeline Context Flow:**
```
PipelineContext
  └─► Planner       → enriched_prompt
      └─► Art Director → style_brief
          └─► DOP         → shot_brief
              └─► Generator  → image
                  └─► Critic    → critiques[]
```

**Configuration-Driven HITL:**
- `AGENT_CONFIG` dictionary maps agent names to workflow metadata
- Single `/api/review/agent` endpoint handles all review gates
- Frontend extracts agent name from stage via regex
- Adding new HITL agent only requires config entry

**Lazy Loading:**
- Generator and Critic agents use lazy loading to avoid circular imports
- Backend models instantiated on-demand via registry

The data flow is unidirectional and predictable:
- User action → API request → Backend processing → Agent execution → Context update → State update → Message push → API response → Frontend render
