import { useState, useRef } from 'react';

export default function StudioLayout() {
  const [prompt, setPrompt] = useState('');
  const [referenceImage, setReferenceImage] = useState(null);
  const [referenceImagePreview, setReferenceImagePreview] = useState(null);
  const [aspectRatio, setAspectRatio] = useState('1:1');
  const [generatedImage, setGeneratedImage] = useState(null);
  const [generatedVideo, setGeneratedVideo] = useState(null);
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
  const [status, setStatus] = useState('');

  const fileInputRef = useRef(null);
  const videoRef = useRef(null);

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setReferenceImage(event.target.result);
        setReferenceImagePreview(event.target.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleCameraCapture = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      const video = document.createElement('video');
      video.srcObject = stream;
      video.play();

      // Wait for video to be ready
      await new Promise((resolve) => {
        video.onloadedmetadata = resolve;
      });

      // Capture frame
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0);

      // Stop camera
      stream.getTracks().forEach(track => track.stop());

      // Convert to base64
      const imageData = canvas.toDataURL('image/png');
      setReferenceImage(imageData);
      setReferenceImagePreview(imageData);
    } catch (err) {
      console.error('Camera access error:', err);
      alert('Failed to access camera. Please check permissions.');
    }
  };

  const handleGenerateImage = async () => {
    if (!prompt.trim()) {
      alert('Please enter a prompt');
      return;
    }

    setIsGeneratingImage(true);
    setStatus('Generating image...');
    setGeneratedImage(null);
    setGeneratedVideo(null);

    try {
      const payload = {
        prompt: prompt.trim(),
        aspect_ratio: aspectRatio,
      };

      if (referenceImage) {
        payload.images = [referenceImage];
      }

      const response = await fetch('/api/generate_image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to generate image');
      }

      if (data.image_data) {
        setGeneratedImage(data.image_data);
        setStatus('Image generated successfully!');
      } else {
        throw new Error('No image data returned');
      }
    } catch (err) {
      console.error('Generation error:', err);
      setStatus(`Error: ${err.message}`);
    } finally {
      setIsGeneratingImage(false);
    }
  };

  const handleGenerateVideo = async () => {
    if (!generatedImage) {
      alert('Generate an image first');
      return;
    }

    setIsGeneratingVideo(true);
    setStatus('Generating video...');

    try {
      const response = await fetch('/api/generate_video', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_url: generatedImage,  // Send base64 image data
          prompt: prompt.trim(),
          aspect_ratio: aspectRatio,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to generate video');
      }

      if (data.video_data) {
        setGeneratedVideo(data.video_data);
        setStatus('Video generated successfully!');
      } else {
        throw new Error('No video data returned');
      }
    } catch (err) {
      console.error('Video generation error:', err);
      setStatus(`Error: ${err.message}`);
    } finally {
      setIsGeneratingVideo(false);
    }
  };

  const handleClearReference = () => {
    setReferenceImage(null);
    setReferenceImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDownloadImage = () => {
    if (generatedImage) {
      const link = document.createElement('a');
      link.href = generatedImage;
      link.download = 'generated_image.png';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const handleDownloadVideo = () => {
    if (generatedVideo) {
      const link = document.createElement('a');
      link.href = generatedVideo;
      link.download = 'generated_video.mp4';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  return (
    <div className="studio-layout">
      {/* Left Column - Inputs */}
      <div className="studio-column inputs-column">
        <h2>Inputs</h2>

        <div className="input-group">
          <label>Prompt</label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe what you want to create..."
            rows={4}
            disabled={isGeneratingImage}
          />
        </div>

        <div className="input-group">
          <label>Aspect Ratio</label>
          <select
            value={aspectRatio}
            onChange={(e) => setAspectRatio(e.target.value)}
            disabled={isGeneratingImage}
          >
            <option value="1:1">1:1 (Square)</option>
            <option value="16:9">16:9 (Landscape)</option>
            <option value="9:16">9:16 (Portrait)</option>
            <option value="4:3">4:3</option>
            <option value="3:4">3:4</option>
          </select>
        </div>

        <div className="input-group">
          <label>Reference Image (Optional)</label>
          <div className="image-input-buttons">
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isGeneratingImage}
              className="secondary"
            >
              Upload Image
            </button>
            <button
              onClick={handleCameraCapture}
              disabled={isGeneratingImage}
              className="secondary"
            >
              Take Photo
            </button>
            {referenceImagePreview && (
              <button
                onClick={handleClearReference}
                disabled={isGeneratingImage}
                className="secondary danger"
              >
                Clear
              </button>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageUpload}
            style={{ display: 'none' }}
          />
          {referenceImagePreview && (
            <div className="reference-preview">
              <img src={referenceImagePreview} alt="Reference" />
            </div>
          )}
        </div>

        <button
          onClick={handleGenerateImage}
          disabled={isGeneratingImage || !prompt.trim()}
          className="primary generate-button"
        >
          {isGeneratingImage ? 'Generating...' : 'Generate Image'}
        </button>

        {status && (
          <div className={`status-message ${status.includes('Error') ? 'error' : 'success'}`}>
            {status}
          </div>
        )}
      </div>

      {/* Middle Column - Generated Image */}
      <div className="studio-column image-column">
        <h2>Generated Image</h2>
        <div className="image-output">
          {generatedImage ? (
            <>
              <img src={generatedImage} alt="Generated" className="generated-image" />
              <button
                onClick={handleDownloadImage}
                className="secondary"
              >
                Download Image
              </button>
              <button
                onClick={handleGenerateVideo}
                disabled={isGeneratingVideo}
                className="primary"
              >
                {isGeneratingVideo ? 'Generating Video...' : 'Generate Video'}
              </button>
            </>
          ) : (
            <div className="placeholder">
              <p>Generated image will appear here</p>
            </div>
          )}
        </div>
      </div>

      {/* Right Column - Generated Video */}
      <div className="studio-column video-column">
        <h2>Generated Video</h2>
        <div className="video-output">
          {generatedVideo ? (
            <>
              <video
                ref={videoRef}
                src={generatedVideo}
                controls
                className="generated-video"
                preload="metadata"
              />
              <button
                onClick={handleDownloadVideo}
                className="secondary"
              >
                Download Video
              </button>
            </>
          ) : (
            <div className="placeholder">
              <p>Generated video will appear here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
