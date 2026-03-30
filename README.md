# Agentic Image Generation Pipeline

A conversational agentic image pipeline with Flask backend and React frontend. This application uses Google's Gemini models to generate images and iteratively improve them through AI critique and human-in-the-loop refinement.

## Features

- **Text-to-Image Generation**: Generate images from text prompts using Gemini 3 Pro Image Preview
- **Multi-Image Composition**: Combine multiple input images (face composition, style blending, element extraction)
- **AI Prompt Inference**: Upload images without text and let AI suggest a composition prompt
- **AI-Powered Critique**: Automatic vision critique with regional issue detection
- **Custom Fixes**: Add unlimited custom fix descriptions alongside AI-detected issues
- **Re-run Critique**: Run critique multiple times at any point in the workflow
- **Aspect Ratio Preservation**: Maintains selected aspect ratio throughout fix pipeline
- **Conversational UI**: Chat-based interface with message bubbles
- **Single-Server Deployment**: Flask serves both API and React frontend

## Architecture

### Technology Stack
- **Backend**: Flask + Google ADK (Agent Development Kit)
- **Frontend**: React + Vite (chat-based UI with message bubbles)
- **Image Generator**: `gemini-3-pro-image-preview`
- **Vision Critic**: `gemini-3.1-pro-preview`
- **Agent Framework**: `gemini-2.0-flash` for agent orchestration
- **Deployment**: Single server (Flask serves both API and static frontend)

### Design Patterns
- **Factory Pattern**: Singleton model instantiation via `ModelFactory`
- **Agent Pattern**: ADK-based agents for critique and fix workflows
- **Message-Based UI**: Chat bubbles render different message types (text, image, options, checklist, etc.)
- **State Management**: Global pipeline state with PIL Image objects

## Project Structure

```
agentic_image_gen_app/
├── backend/
│   ├── app.py                    # Flask app + all routes
│   ├── state.py                  # Global pipeline state + message queue
│   ├── agent.py                  # ADK agent runner
│   ├── factory.py                # ModelFactory (singleton pattern)
│   ├── config.py                 # Configuration + environment
│   ├── schemas.py                # Pydantic models
│   ├── models/
│   │   ├── generator.py          # Image generation + inpainting
│   │   └── critic.py             # Vision critique + prompt inference
│   ├── pipeline/
│   │   ├── tools.py              # ADK tools (generate, critique, apply_fix, etc.)
│   │   └── composer.py           # Image utilities (crop, mask, annotate)
│   ├── agents/
│   │   ├── critique_agent.yaml   # ADK agent for running critique
│   │   ├── fix_loop.yaml         # ADK agent for applying fixes
│   │   └── generation_agent.yaml # ADK agent for generation
│   ├── outputs/                  # Generated images directory
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx              # React entry point
        ├── App.jsx               # Main app with message handling
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
        │   ├── OptionsBubble.jsx      # Multiple choice buttons
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

### 2. Image Generation
- **Option A**: Enter text prompt
- **Option B**: Upload multiple images (AI will infer composition prompt)
- **Option C**: Upload images + text prompt for guided composition
- Click "Generate Image"

### 3. Initial Review
- Review generated image
- Options:
  - **✓ Looks good — critique it**: Proceed to automatic AI critique
  - **✎ Edit my prompt**: Modify prompt and regenerate
  - **✕ Start over**: Reset workflow

### 4. Critique Review
- AI automatically critiques the image against the prompt
- View:
  - **Critique score** and assessment
  - **Annotated image** with bounding boxes around issues
  - **Checklist** of detected fixes (HIGH, MEDIUM, LOW severity)
- Actions:
  - **Select AI-detected fixes** to apply
  - **+ Add Custom Fix**: Add your own fix descriptions
  - **🔄 Run Critique Again**: Re-run critique on current image
  - **Apply Selected Fixes**: Apply all checked fixes at once

### 5. Fix Review
- View before/after comparison
- Options:
  - **✓ Accept & Finalize**: Save fixed image as final
  - **✕ Reject & Keep Original**: Discard fixes
  - **🔄 Run Critique Again**: Critique the fixed image and iterate

### 6. Iterate or Finalize
- Can run critique → fixes → critique cycle multiple times
- When satisfied, finalize to download

## Data Flow

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed data flow diagrams.

### High-Level Flow

```
User Input → Generation → Critique → Fix Selection → Apply Fixes → Review
                ↑                                                      ↓
                └──────────────── Re-critique Loop ────────────────────┘
```

## API Endpoints

### Core Endpoints
- `GET /api/status` - Get current pipeline stage
- `POST /api/generate` - Generate new image (text + optional images)
- `POST /api/review/initial` - Accept/reject/edit initial image
- `POST /api/recritique` - Re-run critique on current image
- `POST /api/review/fixes` - Apply selected fixes (AI + custom)
- `POST /api/fix/accept` - Accept or reject applied fixes

### Static Assets
- `GET /outputs/<filename>` - Serve generated images
- `GET /` - Serve React frontend

## Pipeline Stages

1. **selecting_aspect_ratio**: User selects image aspect ratio
2. **idle**: Ready to accept generation request
3. **generating**: Image generation in progress
4. **awaiting_initial_review**: User reviews initial image
5. **critiquing**: AI critique in progress
6. **awaiting_fix_review**: User selects fixes (AI + custom)
7. **applying_fixes**: Fixes being applied
8. **awaiting_fixes_review**: User reviews applied fixes
9. **running_critique**: Re-running critique
10. **done**: Final image ready

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
