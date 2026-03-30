import { useState, useRef } from "react";

export default function InputBar({ onSend, disabled, placeholder }) {
  const [text, setText] = useState("");
  const [images, setImages] = useState([]);
  const textRef = useRef(null);
  const fileRef = useRef(null);

  const submit = () => {
    const val = text.trim();
    if ((!val && images.length === 0) || disabled) return;
    setText("");
    setImages([]);
    textRef.current.style.height = "auto";
    onSend(val, images);
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
  };

  const onInput = (e) => {
    setText(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = e.target.scrollHeight + "px";
  };

  const handleImageUpload = (e) => {
    const files = Array.from(e.target.files);
    files.forEach(file => {
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (ev) => {
          setImages(prev => [...prev, { name: file.name, data: ev.target.result }]);
        };
        reader.readAsDataURL(file);
      }
    });
    e.target.value = null; // Reset input
  };

  const removeImage = (index) => {
    setImages(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="input-bar-container">
      {images.length > 0 && (
        <div className="image-previews">
          {images.map((img, i) => (
            <div key={i} className="image-preview">
              <img src={img.data} alt={img.name} />
              <button className="remove-img-btn" onClick={() => removeImage(i)}>×</button>
            </div>
          ))}
        </div>
      )}
      <div className="input-bar">
        <button
          className="attach-btn"
          onClick={() => fileRef.current?.click()}
          disabled={disabled}
          title="Attach images"
        >
          📎
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          multiple
          style={{ display: 'none' }}
          onChange={handleImageUpload}
        />
        <textarea ref={textRef} value={text} onInput={onInput} onKeyDown={onKey}
          placeholder={placeholder} disabled={disabled} rows={1} />
        <button className="send-btn" onClick={submit} disabled={disabled || (!text.trim() && images.length === 0)}>↑</button>
      </div>
    </div>
  );
}
