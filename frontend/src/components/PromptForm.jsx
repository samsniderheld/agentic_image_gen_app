import { useState } from 'react';
import { generate } from '../api';

export default function PromptForm({ onAdvance }) {
  const [prompt, setPrompt] = useState('');
  const [aspectRatio, setAspectRatio] = useState('1:1');
  const [seed, setSeed] = useState('');
  const [loading, setLoading] = useState(false);
  const [inputImages, setInputImages] = useState([]);
  const [inputPreviews, setInputPreviews] = useState([]);

  const handleImageUpload = (e) => {
    const files = Array.from(e.target.files);
    const promises = files.map(file => {
      return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.readAsDataURL(file);
      });
    });

    Promise.all(promises).then(results => {
      setInputImages([...inputImages, ...results]);
      setInputPreviews([...inputPreviews, ...results]);
    });
  };

  const removeImage = (index) => {
    setInputImages(inputImages.filter((_, i) => i !== index));
    setInputPreviews(inputPreviews.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const form = {
        prompt,
        aspect_ratio: aspectRatio,
        ...(seed && { seed: parseInt(seed) }),
        ...(inputImages.length > 0 && { input_images: inputImages })
      };

      // Show generating state immediately
      onAdvance("generating", {});

      // Generate returns critique automatically now
      const res = await generate(form);

      // Response includes stage="awaiting_fix_review" and critique data
      onAdvance(res.stage, res);
    } catch (error) {
      console.error("Generation failed:", error);
      alert("Failed to generate image. Please try again.");
      onAdvance("idle", {});
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      <h1>Agentic Image Generator</h1>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px' }}>
            Input Images (optional - for composition):
          </label>
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={handleImageUpload}
            disabled={loading}
            style={{ marginBottom: '10px' }}
          />
          {inputPreviews.length > 0 && (
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginTop: '10px' }}>
              {inputPreviews.map((preview, idx) => (
                <div key={idx} style={{ position: 'relative' }}>
                  <img
                    src={preview}
                    alt={`Input ${idx + 1}`}
                    style={{ width: '100px', height: '100px', objectFit: 'cover', borderRadius: '4px' }}
                  />
                  <button
                    type="button"
                    onClick={() => removeImage(idx)}
                    disabled={loading}
                    style={{
                      position: 'absolute',
                      top: '-5px',
                      right: '-5px',
                      backgroundColor: '#dc3545',
                      color: 'white',
                      border: 'none',
                      borderRadius: '50%',
                      width: '24px',
                      height: '24px',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px' }}>Aspect Ratio:</label>
          <select
            value={aspectRatio}
            onChange={(e) => setAspectRatio(e.target.value)}
            style={{ padding: '8px', width: '200px' }}
            disabled={loading}
          >
            <option value="1:1">1:1 (Square)</option>
            <option value="16:9">16:9 (Landscape)</option>
            <option value="9:16">9:16 (Portrait)</option>
            <option value="4:3">4:3 (Classic)</option>
          </select>
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px' }}>
            Prompt {inputImages.length > 0 && <span style={{ fontSize: '12px', color: '#666' }}>(optional - AI will suggest composition if empty)</span>}:
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={4}
            style={{ width: '100%', padding: '8px' }}
            placeholder={
              inputImages.length > 0
                ? "Leave empty to let AI suggest a composition prompt, or describe your desired composition..."
                : "E.g., 'A serene mountain landscape at sunset'"
            }
            required={inputImages.length === 0}
            disabled={loading}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px' }}>Seed (optional):</label>
          <input
            type="number"
            value={seed}
            onChange={(e) => setSeed(e.target.value)}
            style={{ padding: '8px', width: '200px' }}
            disabled={loading}
          />
        </div>

        <button
          type="submit"
          disabled={loading || (inputImages.length === 0 && !prompt.trim())}
          style={{
            padding: '10px 20px',
            backgroundColor: loading || (inputImages.length === 0 && !prompt.trim()) ? '#ccc' : '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading || (inputImages.length === 0 && !prompt.trim()) ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? 'Generating...' : inputImages.length > 0 && !prompt.trim() ? 'Generate with AI Prompt' : 'Generate Image'}
        </button>
        {inputImages.length > 0 && !prompt.trim() && (
          <p style={{ fontSize: '12px', color: '#666', marginTop: '10px' }}>
            💡 AI will analyze your images and suggest a composition prompt automatically
          </p>
        )}
      </form>
    </div>
  );
}
