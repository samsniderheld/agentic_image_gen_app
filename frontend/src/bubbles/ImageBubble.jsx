import { useState } from 'react';

export default function ImageBubble({ message }) {
  const [enlarged, setEnlarged] = useState(false);

  return (
    <>
      <div className="image-bubble" onClick={() => setEnlarged(true)}>
        <img src={message.src} alt={message.caption} />
        {message.caption && <div className="image-caption">{message.caption}</div>}
      </div>

      {enlarged && (
        <div className="image-modal" onClick={() => setEnlarged(false)}>
          <div className="image-modal-content">
            <img src={message.src} alt={message.caption} />
          </div>
        </div>
      )}
    </>
  );
}
