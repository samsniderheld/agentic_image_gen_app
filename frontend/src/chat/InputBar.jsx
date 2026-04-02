import { useState, useRef } from 'react';

export default function InputBar({ onSend, disabled, stage }) {
  const [text, setText] = useState('');
  const [images, setImages] = useState([]);
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);

  const handleSend = () => {
    if (text.trim() || images.length > 0) {
      onSend({ text: text.trim(), images });
      setText('');
      setImages([]);
    }
  };

  const handleKeyDown = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    files.forEach((file) => {
      const reader = new FileReader();
      reader.onload = (evt) => {
        setImages((prev) => [...prev, evt.target.result]);
      };
      reader.readAsDataURL(file);
    });
  };

  const removeImage = (idx) => {
    setImages(images.filter((_, i) => i !== idx));
  };

  // Auto-resize textarea
  const handleTextChange = (e) => {
    setText(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  };

  if (stage === 'idle') {
    return null; // Input is shown only after aspect ratio is selected
  }

  return (
    <div className={`input-bar ${disabled ? 'input-bar-disabled' : ''}`}>
      {disabled && (
        <div className="input-processing">
          <div className="processing-spinner"></div>
          <span>Processing...</span>
        </div>
      )}

      {images.length > 0 && (
        <div className="image-previews">
          {images.map((img, idx) => (
            <div key={idx} className="image-preview">
              <img src={img} alt={`Upload ${idx + 1}`} />
              <button className="image-preview-remove" onClick={() => removeImage(idx)}>
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="input-controls">
        <button
          className="input-upload"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
        >
          📎
        </button>
        <textarea
          ref={textareaRef}
          className="input-textarea"
          placeholder={disabled ? "Processing..." : "Describe your image..."}
          value={text}
          onChange={handleTextChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
        />
        <button
          className="input-send"
          onClick={handleSend}
          disabled={disabled || (!text.trim() && images.length === 0)}
        >
          {disabled ? '...' : 'Send'}
        </button>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />
    </div>
  );
}
