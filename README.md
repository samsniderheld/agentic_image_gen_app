# Agentic Image Generation Pipeline

A minimal local agentic image pipeline with a Flask backend and React frontend. This application uses Google's Gemini models to generate images and iteratively improve them based on AI critique.

**✨ Features:**
- Text-to-image generation
- Multi-image composition (combine multiple images)
- AI-powered critique with regional fixes
- Integration analysis for composed images
- Iterative refinement workflow
- Single-server deployment

## Architecture

- **Backend**: Flask + Factory Pattern for model instantiation
- **Frontend**: React + Vite (served by Flask in production)
- **Image Generator**: `gemini-3-pro-image-preview`
- **Vision Critic**: `gemini-2.0-flash`
- **Deployment**: Single server (Flask serves both API and static frontend)

## Project Structure

```
agentic_image_gen_app/
├── backend/
│   ├── app.py               # Flask app + all routes
│   ├── state.py             # Single global pipeline state
│   ├── factory.py           # ModelFactory
│   ├── agent.py             # Stateless pipeline step functions
│   ├── models/
│   │   ├── generator.py     # gemini-3-pro-image-preview
│   │   └── critic.py        # gemini-2.0-flash
│   ├── pipeline/
│   │   └── composer.py      # Crop / recomposite (PIL only)
│   ├── schemas.py
│   ├── config.py
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── api.js
        └── components/
            ├── PromptForm.jsx
            ├── ImageReview.jsx
            ├── CritiquePanel.jsx
            ├── PatchReview.jsx
            └── FinalResult.jsx
```

## Quick Start (Single Server)

### Prerequisites

- Python 3.8+
- Node.js 16+ (only needed for initial build)
- Google API key with access to Gemini models

### Setup & Run

1. **Install backend dependencies:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your GOOGLE_API_KEY
   ```

3. **Build frontend:**
   ```bash
   cd ../frontend
   npm install
   npm run build
   ```

4. **Start the server:**
   ```bash
   cd ..
   ./start.sh
   # Or manually: cd backend && python app.py
   ```

5. **Open browser:**
   ```
   http://localhost:8000
   ```

The Flask server now serves both the API (`/api/*`) and the React frontend.

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

## Usage

1. Open your browser to `http://localhost:5173`
2. Enter a prompt for image generation
3. Select aspect ratio and optional seed
4. Click "Generate Image"
5. Review the generated image:
   - **Accept**: Proceed to critique
   - **Reject**: Start over
   - **Edit**: Modify prompt and regenerate
6. Review critique results and select fixes to apply
7. Review each patch individually (accept or skip)
8. Download the final image or start over

## Pipeline Stages

1. **idle**: Ready to accept new generation request
2. **generating**: Image generation in progress
3. **awaiting_initial_review**: User reviews initial image
4. **awaiting_fix_review**: User selects which fixes to apply
5. **awaiting_patch_review**: User reviews each patch
6. **done**: Final image ready

## API Endpoints

- `GET /api/status` - Get current pipeline stage
- `POST /api/generate` - Generate new image
- `POST /api/review/initial` - Accept/reject/edit initial image
- `POST /api/review/fixes` - Select fixes to apply
- `POST /api/fix/accept` - Accept or skip individual fix
- `GET /outputs/<filename>` - Serve generated images

## Development

### Backend Testing

Test individual components:

```bash
# Test generator model
python -c "from factory import ModelFactory; from PIL import Image; img = ModelFactory.get_generator().generate('a red car'); img.save('test.png')"

# Test routes with curl
curl http://localhost:8000/api/status
```

### Frontend Development

The frontend uses Vite's proxy to forward API requests to the backend. All `/api` and `/outputs` requests are automatically proxied to `http://localhost:8000`.

## Notes

- Single-user, no authentication
- One global pipeline state
- All models use the same `GOOGLE_API_KEY`
- Images are saved to `backend/outputs/` directory
- No database required
