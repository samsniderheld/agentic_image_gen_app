# Agentic Image Generation Pipeline

A conversational agentic image pipeline with Flask backend and React frontend. This application uses Google's Gemini models to generate images and iteratively improve them through AI critique and human-in-the-loop refinement.

## Features

- **Text-to-Image Generation**: Generate images from text prompts using Gemini 3 Pro Image Preview
- **Multi-Image Composition**: Combine multiple input images (face composition, style blending, element extraction)
- **AI Prompt Inference**: Upload images without text and let AI suggest a composition prompt
- **AI-Powered Critique**: Automatic vision critique with full-image issue detection
- **Custom Fixes**: Add unlimited custom fix descriptions alongside AI-detected issues
- **Re-run Critique**: Run critique multiple times at any point in the workflow
- **Aspect Ratio Preservation**: Maintains selected aspect ratio throughout fix pipeline
- **Conversational UI**: Chat-based interface with message bubbles
- **Single-Server Deployment**: Flask serves both API and React frontend

## Architecture

### Technology Stack
- **Backend**: Flask + Python ABC-based agent pipeline
- **Frontend**: React + Vite (chat-based UI with message bubbles)
- **Image Generator**: `gemini-3-pro-image-preview`
- **Vision Critic**: `gemini-3.1-pro-preview`
- **Agent Models**: `gemini-3.1-pro-preview` for pre-generation agents (planner, art director, DOP)
- **Deployment**: Single server (Flask serves both API and static frontend)

### Design Patterns
- **ABC Pattern**: Abstract base classes for extensible agent system
- **Registry Pattern**: Agent and model registration via centralized registry
- **Pipeline Pattern**: Sequential agent execution with context passing
- **Human-in-the-Loop (HITL)**: Review gates between each agent with feedback loops
- **Configuration-Driven**: Single AGENT_CONFIG dictionary drives all review workflows
- **Message-Based UI**: Chat bubbles render different message types (text, image, options, checklist, etc.)
- **PipelineContext**: Dataclass object flows through all agents, accumulating outputs
- **Full-Image Fixes**: All fixes apply to entire image using inpainting, no regional bounding boxes

## Project Structure

```
agentic_image_gen_app/
├── backend/
│   ├── app.py                    # Flask app + all routes + AGENT_CONFIG
│   ├── state.py                  # Global pipeline state + message queue + pipeline_context
│   ├── agent.py                  # Pipeline runner functions (pre/post/generator)
│   ├── config.py                 # Configuration + environment
│   ├── schemas.py                # Pydantic models
│   ├── models/
│   │   ├── base.py               # ABC definitions (ImageGenerator, ImageCritic, PipelineAgent)
│   │   ├── registry.py           # Agent/model registration and factory functions
│   │   ├── pipeline_context.py   # PipelineContext dataclass
│   │   ├── generators/
│   │   │   └── gemini.py         # GeminiGenerator (image generation + inpainting)
│   │   └── critics/
│   │       └── gemini.py         # GeminiCritic (vision critique + prompt inference)
│   ├── pipeline/
│   │   └── tools.py              # Fix application tool (apply_all_fixes)
│   ├── agents/
│   │   ├── planner_agent.py      # Prompt enrichment agent
│   │   ├── art_director_agent.py # Visual style definition agent
│   │   ├── dop_agent.py          # Shot specification agent
│   │   ├── generator_agent.py    # Image generation wrapper agent
│   │   └── critic_agent.py       # Critique wrapper agent
│   ├── outputs/                  # Generated images directory
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx              # React entry point
        ├── App.jsx               # Main app with message handling + stage routing
        ├── api.js                # API client functions
        ├── styles.css            # Global styles (dark theme)
        ├── chat/
        │   ├── Message.jsx       # Message router component
        │   ├── MessageList.jsx   # Scrollable message container
        │   └── InputBar.jsx      # Text input + image upload
        ├── bubbles/
        │   ├── TextBubble.jsx         # Simple text messages
        │   ├── ThinkingBubble.jsx     # Agent thinking messages
        │   ├── ImageBubble.jsx        # Image display
        │   ├── ComparisonBubble.jsx   # Before/after comparison
        │   ├── OptionsBubble.jsx      # Multiple choice buttons + feedback input
        │   ├── ChecklistBubble.jsx    # Fix selection + custom fixes
        │   ├── CritiqueBubble.jsx     # Critique score display
        │   ├── InputRequestBubble.jsx # Prompt for text input
        │   └── FinalBubble.jsx        # Final image with download
        └── components/
            ├── PromptForm.jsx         # Initial generation form
            ├── ImageReview.jsx        # (legacy, not used)
            ├── CritiquePanel.jsx      # (legacy, not used)
            ├── PatchReview.jsx        # (legacy, not used)
            └── FinalResult.jsx        # (legacy, not used)
```

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+ (only needed for frontend build)
- Google API key with access to Gemini models

### Setup & Run

1. **Clone and navigate:**
   ```bash
   cd agentic_image_gen_app
   ```

2. **Install backend dependencies:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your GOOGLE_API_KEY
   ```

4. **Build frontend:**
   ```bash
   cd ../frontend
   npm install
   npm run build
   ```

5. **Start the server:**
   ```bash
   cd ../backend
   python app.py
   ```

6. **Open browser:**
   ```
   http://localhost:8000
   ```

The Flask server serves both the API (`/api/*`) and the React frontend.

---

## Development Mode (Two Servers)

For active frontend development with hot reload:

### Backend (Terminal 1)
```bash
cd backend
source venv/bin/activate
python app.py
# Runs on http://localhost:8000
```

### Frontend (Terminal 2)
```bash
cd frontend
npm run dev
# Runs on http://localhost:5173 with proxy to backend
```

Visit `http://localhost:5173` for development with hot module replacement.

## Usage Workflow

### 1. Initial Setup
- Open browser to `http://localhost:8000` (or `http://localhost:5173` in dev mode)
- Select aspect ratio (1:1, 16:9, 9:16, 4:3)

### 2. Prompt Planning (HITL Gate 1)
- **Option A**: Enter text prompt
- **Option B**: Upload multiple images (AI will infer composition prompt)
- **Option C**: Upload images + text prompt for guided composition
- Click "Generate Image"
- **Planner agent** expands your prompt into a detailed generation brief
- Review enriched prompt:
  - **✓ Approve**: Continue to style definition
  - **✎ Give feedback**: Planner re-runs with your input
  - **✕ Start over**: Reset workflow

### 3. Visual Style Definition (HITL Gate 2)
- **Art Director agent** defines the visual style (medium, color grading, texture, etc.)
- Review style brief:
  - **✓ Approve**: Continue to shot setup
  - **✎ Give feedback**: Art Director revises based on your input
  - **✕ Start over**: Reset workflow

### 4. Shot Specification (HITL Gate 3)
- **DOP agent** sets up camera angle, framing, and focal length
- Review shot brief:
  - **✓ Approve**: Generate image
  - **✎ Give feedback**: DOP adjusts shot setup
  - **✕ Start over**: Reset workflow

### 5. Image Generation
- **Generator agent** combines all briefs and generates the image
- Review generated image:
  - **✓ Looks good — critique it**: Proceed to automatic AI critique
  - **✕ Start over**: Reset workflow

### 6. Critique Review
- **Critic agent** automatically critiques the image against the prompt
- View:
  - **Critique score** and assessment
  - **Current image** being evaluated
  - **Checklist** of detected fixes (HIGH, MEDIUM, LOW severity)
- Actions:
  - **Select AI-detected fixes** to apply (fixes apply to entire image)
  - **+ Add Custom Fix**: Add your own fix descriptions
  - **🔄 Run Critique Again**: Re-run critique on current image
  - **Apply Selected Fixes**: Apply all checked fixes at once using full-image inpainting

### 7. Fix Review
- View before/after comparison
- Options:
  - **✓ Accept & Finalize**: Save fixed image as final
  - **✕ Reject & Keep Original**: Discard fixes
  - **🔄 Run Critique Again**: Critique the fixed image and iterate

### 8. Iterate or Finalize
- Can run critique → fixes → critique cycle multiple times
- When satisfied, finalize to download

## Data Flow

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed data flow diagrams.

### High-Level Flow

```
User Input → Planner (review) → Art Director (review) → DOP (review) → Generation
    ↑            ↓                    ↓                     ↓              ↓
    └─────── Start Over ───────────────────────────────────────────────────┘
                                                                           ↓
                                                    Critique → Fix Selection → Apply Fixes → Review
                                                       ↑                                       ↓
                                                       └────── Re-critique Loop ───────────────┘
```

## API Endpoints

### Core Endpoints
- `GET /api/status` - Get current pipeline stage
- `POST /api/generate` - Start pipeline with user prompt (runs planner agent)
- `POST /api/review/agent` - Generic agent review endpoint (approve/feedback/reject)
- `POST /api/critique` - Run critique on current image (initial or re-critique)
- `POST /api/review/fixes` - Apply selected fixes (AI + custom) to entire image
- `POST /api/fix/accept` - Accept or reject applied fixes

### Static Assets
- `GET /outputs/<filename>` - Serve generated images
- `GET /` - Serve React frontend

## Pipeline Stages

1. **selecting_aspect_ratio**: User selects image aspect ratio
2. **idle**: Ready to accept generation request
3. **running_planner**: Planner agent enriching prompt
4. **awaiting_planner_review**: User reviews enriched prompt (approve/feedback/reject)
5. **awaiting_art_director_review**: User reviews style brief (approve/feedback/reject)
6. **awaiting_dop_review**: User reviews shot setup (approve/feedback/reject)
7. **awaiting_initial_review**: User reviews generated image
8. **critiquing**: Critic agent running
9. **awaiting_fix_review**: User selects fixes (AI + custom)
10. **applying_fixes**: Fixes being applied to image
11. **awaiting_fixes_review**: User reviews applied fixes
12. **running_critique**: Re-running critique
13. **done**: Final image ready

## Message Types

The chat UI uses different message types rendered as bubbles:

- **text**: Simple text message (user or agent)
- **thinking**: Agent processing indicator (collapsible)
- **image**: Image display with optional caption
- **comparison**: Side-by-side before/after images
- **options**: Multiple choice buttons
- **checklist**: Fix selection with custom fix support
- **critique**: Critique score and assessment display
- **input_request**: Prompt for user text input
- **final**: Final image with download button

## Key Features Explained

### Multi-Image Composition
Upload 2+ images without a prompt, and the AI will analyze them and suggest a composition task focusing on:
- Face composition and merging
- Style blending and transfer
- Object compositing
- Scene merging
- Element extraction

### Custom Fixes
- After AI critique, click "+ Add Custom Fix"
- Describe any change you want in plain text
- Custom fixes appear with "CUSTOM" severity tag
- Apply alongside AI-detected fixes

### Re-run Critique
Available at two points:
1. **In fix selection**: Button next to "Apply Selected Fixes"
2. **After applying fixes**: Option alongside "Accept & Finalize"

Allows iterative refinement:
- Apply fixes → critique → add more fixes → critique → finalize

### Aspect Ratio Preservation
- Selected aspect ratio is stored in state
- All fixes (inpainting) use the same aspect ratio
- Ensures consistency across iterations

## Development

### Backend Testing

```bash
# Test generator model
python -c "from factory import ModelFactory; img = ModelFactory.get_generator().generate('a red car'); img.save('test.png')"

# Test critic model
python -c "from factory import ModelFactory; from PIL import Image; img = Image.open('test.png'); result = ModelFactory.get_critic().critique(img, 'a red car'); print(result)"

# Test API
curl http://localhost:8000/api/status
```

### Frontend Development

The frontend uses Vite's proxy to forward API requests to the backend:
- All `/api/*` requests → `http://localhost:8000`
- All `/outputs/*` requests → `http://localhost:8000`

After making changes:
```bash
cd frontend
npm run build
```

### Adding New Message Types

1. Create bubble component in `frontend/src/bubbles/`
2. Add case to `Message.jsx` router
3. Backend pushes message with new type via `state.push_message()`

## Configuration

### Environment Variables

```bash
# backend/.env
GOOGLE_API_KEY=your_api_key_here
```

### Model Configuration

Edit `backend/models/generator.py` or `backend/models/critic.py` to change:
- Model names
- Generation parameters
- Safety settings
- Temperature/top-k/top-p

## Notes

- **Single-user**: No authentication, one global state
- **No database**: All state in memory, images in `outputs/`
- **Aspect ratios**: 1:1, 16:9, 9:16, 4:3 supported
- **Image formats**: PNG output, base64 input
- **State persistence**: Lost on server restart
- **Concurrent users**: Not supported (global state)

## Troubleshooting

### Frontend not loading
```bash
cd frontend && npm run build
```

### API errors
- Check `GOOGLE_API_KEY` in `backend/.env`
- Verify API key has access to Gemini models
- Check backend logs for stack traces

### Images not displaying
- Verify `backend/outputs/` directory exists
- Check browser console for 404s
- Ensure Flask is serving from correct directory

## License

MIT
