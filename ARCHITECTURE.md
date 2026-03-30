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
│  │  - User input handling                                    │  │
│  │  - Image upload/display                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             │ /api/* requests                    │
│                             ▼                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   Flask API Routes                        │  │
│  │  - /api/generate                                          │  │
│  │  - /api/review/initial                                    │  │
│  │  - /api/recritique                                        │  │
│  │  - /api/review/fixes                                      │  │
│  │  - /api/fix/accept                                        │  │
│  └─────────────┬─────────────────────────────────────────────┘  │
│                │                                                 │
│                ▼                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   Global State                            │  │
│  │  - pipeline: {stage, request, image_path, ...}            │  │
│  │  - messages: [...]                                        │  │
│  │  - PIL Image objects in memory                            │  │
│  └─────────────┬─────────────────────────────────────────────┘  │
│                │                                                 │
│                ▼                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 ADK Agent Runner                          │  │
│  │  - Runs YAML-defined agents                               │  │
│  │  - Manages tool execution                                 │  │
│  └─────────────┬─────────────────────────────────────────────┘  │
│                │                                                 │
│                ▼                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 Model Factory                             │  │
│  │  - Singleton GeneratorModel (gemini-3-pro-image-preview)  │  │
│  │  - Singleton CriticModel (gemini-3.1-pro-preview)         │  │
│  └─────────────┬─────────────────────────────────────────────┘  │
│                │                                                 │
└────────────────┼─────────────────────────────────────────────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │   Google Gemini API    │
    │  - Image Generation    │
    │  - Vision Critique     │
    │  - Agent Orchestration │
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
│                          ├─► /api/generate
│                          ├─► /api/review/initial
│                          ├─► /api/recritique
│                          ├─► /api/review/fixes
│                          └─► /api/fix/accept
│
├── state.py ────────────► Global State Management
│                          │
│                          ├─► pipeline: dict
│                          ├─► messages: list
│                          ├─► push_message()
│                          └─► reset()
│
├── agent.py ────────────► ADK Agent Executor
│                          │
│                          └─► run_adk_segment()
│
├── factory.py ──────────► Singleton Model Factory
│                          │
│                          ├─► get_generator() → GeneratorModel
│                          └─► get_critic() → CriticModel
│
├── models/
│   ├── generator.py ────► Image Generation + Inpainting
│   │                      │
│   │                      ├─► generate(prompt, aspect_ratio, input_images)
│   │                      └─► inpaint(image, mask, prompt, aspect_ratio)
│   │
│   └── critic.py ───────► Vision Critique + Prompt Inference
│                          │
│                          ├─► critique(image, prompt, input_images)
│                          └─► infer_composition_prompt(images)
│
├── pipeline/
│   ├── tools.py ────────► ADK Tool Definitions
│   │                      │
│   │                      ├─► generate_image()
│   │                      ├─► critique_image()
│   │                      ├─► apply_fix()
│   │                      ├─► apply_all_fixes()
│   │                      └─► exit_loop()
│   │
│   └── composer.py ─────► Image Utilities
│                          │
│                          ├─► crop_region()
│                          ├─► create_mask()
│                          ├─► recomposite()
│                          └─► annotate_bboxes()
│
├── agents/
│   ├── critique_agent.yaml ──► Runs critique_image tool
│   ├── fix_loop.yaml ─────────► Iterates through fixes
│   └── generation_agent.yaml ─► Runs generate_image tool
│
└── schemas.py ──────────► Pydantic Models
                           │
                           ├─► GenerationRequest
                           ├─► CritiqueResult
                           ├─► RegionalFix
                           └─► ImageIntegration
```

### Frontend Components

```
frontend/src/
│
├── App.jsx ─────────────► Main Application
│                          │
│                          ├─► Message state management
│                          ├─► Event handlers (handleOption, handleChecklist, handleRecritique)
│                          └─► Stage tracking
│
├── api.js ──────────────► API Client
│                          │
│                          ├─► generate(form)
│                          ├─► reviewInitial(decision, new_prompt)
│                          ├─► recritique()
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
│   ├── OptionsBubble.jsx ───────► Multiple choice
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

### 1. Initial Generation Flow

```
User Input (Form)
    │
    │ {prompt, aspect_ratio, seed, input_images[base64]}
    ▼
POST /api/generate
    │
    ├─► Decode base64 images → PIL Images
    ├─► Create GenerationRequest
    ├─► Update state.pipeline
    │   └─► {stage: "generating", aspect_ratio, input_images, ...}
    │
    ├─► If no prompt + images exist:
    │   └─► infer_composition_prompt(images)
    │
    ├─► ModelFactory.get_generator().generate()
    │   └─► Gemini API (gemini-3-pro-image-preview)
    │       └─► Returns PIL Image
    │
    ├─► Save: outputs/00_initial.png
    ├─► Update state.pipeline["image_path"]
    │
    ├─► Push messages:
    │   ├─► {type: "thinking", content: "Generating..."}
    │   ├─► {type: "text", content: "Done!"}
    │   ├─► {type: "image", url: "/outputs/00_initial.png"}
    │   └─► {type: "options", options: [accept, edit, reject]}
    │
    └─► Return {stage: "awaiting_initial_review", messages: [...]}
        │
        ▼
Frontend receives messages
    │
    └─► Renders message bubbles
```

### 2. Critique Flow

```
User clicks "✓ Looks good — critique it"
    │
    ▼
handleOption("accept")
    │
    ▼
POST /api/review/initial
    │
    ├─► Push messages:
    │   ├─► {type: "user", content: "Looks good, critique it"}
    │   └─► {type: "thinking", content: "Running critique..."}
    │
    ├─► agent.run_adk_segment("critique_agent", ...)
    │   │
    │   ├─► ADK loads agents/critique_agent.yaml
    │   ├─► Calls tools.critique_image(image_path, prompt)
    │   │   │
    │   │   ├─► ModelFactory.get_critic().critique(image, prompt)
    │   │   │   └─► Gemini API (gemini-3.1-pro-preview)
    │   │   │       └─► Returns CritiqueResult
    │   │   │
    │   │   └─► annotate_bboxes(image, fixes)
    │   │       └─► Save: outputs/01_annotated.png
    │   │
    │   └─► Returns critique JSON
    │
    ├─► Update state.pipeline["critique"]
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
    │   └─► Custom fixes converted to RegionalFix format
    │
    ├─► If no fixes selected:
    │   ├─► Save final.png
    │   └─► Return {stage: "done"}
    │
    ├─► Push message: {type: "thinking", content: "Applying fixes..."}
    │
    ├─► tools.apply_all_fixes(image_path, fixes_json)
    │   │
    │   ├─► Load image
    │   ├─► Create annotated version with bounding boxes
    │   ├─► Build combined fix prompt
    │   ├─► ModelFactory.get_generator().inpaint()
    │   │   │
    │   │   └─► Gemini API with:
    │   │       ├─► annotated image (shows what to fix)
    │   │       ├─► full mask (edit entire image)
    │   │       ├─► fix instructions
    │   │       └─► aspect_ratio from state
    │   │
    │   └─► Save: outputs/fixes_applied.png
    │
    ├─► Update state.pipeline["fixed_image_path"]
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
    └─► Backend creates RegionalFix:
        {
          region_id: "custom_0",
          bbox: [0, 0, 100, 100],  // Full image
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
    "stage": str,              # Current workflow stage
    "request": dict,           # GenerationRequest data
    "image_path": str,         # Path to current/original image
    "fixed_image_path": str,   # Path to fixed image (if exists)
    "input_images": [PIL.Image],  # Input images for composition
    "aspect_ratio": str,       # Selected aspect ratio
    "critique": dict,          # CritiqueResult data
    "critique_json": dict,     # Raw critique from agent
    "messages": [dict],        # Message queue for chat UI
}
```

### State Transitions

```
selecting_aspect_ratio
    │
    ▼ User selects aspect ratio
idle
    │
    ▼ User submits generation form
generating
    │
    ▼ Image generated
awaiting_initial_review
    │
    ├─► User clicks "accept" ────► critiquing ────► awaiting_fix_review
    ├─► User clicks "edit" ──────► awaiting_edit ──► (regenerate) ──► generating
    └─► User clicks "reject" ────► idle

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
        "region_id": "fix_1",
        "bbox": [10, 20, 200, 150],
        "severity": "high",
        "issue_description": "Sky lacks depth and vibrancy",
        "fix_prompt": "Enhance sky with deeper blues and dramatic clouds"
      }
    ]
  },
  "messages": [
    {"role": "agent", "type": "critique", "score": 7.5, "assessment": "...", "passed": false},
    {"role": "agent", "type": "image", "url": "/outputs/01_annotated.png", "caption": "Issues annotated"},
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
    {"role": "agent", "type": "image", "url": "/outputs/01_annotated.png", "caption": "Issues annotated"},
    {"role": "agent", "type": "checklist", "prompt": "No issues found! You can finalize the image:", "items": [], "allowRecritique": true}
  ]
}
```

---

## Summary

This architecture provides:

1. **Clean Separation**: Backend handles state/logic, frontend handles UI
2. **Message-Based UI**: Flexible chat interface that can render any message type
3. **Iterative Refinement**: Critique → Fix → Re-critique loop
4. **Human-in-the-Loop**: User controls at every decision point
5. **Extensibility**: Easy to add new message types and workflow stages
6. **Single-Server**: Simple deployment with Flask serving everything

The data flow is unidirectional and predictable:
- User action → API request → Backend processing → State update → Message push → API response → Frontend render
