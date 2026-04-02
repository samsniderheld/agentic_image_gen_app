import { useState } from 'react';

export default function ThinkingBubble({ message }) {
  const [collapsed, setCollapsed] = useState(false);

  if (collapsed) {
    return (
      <div className="thinking-bubble collapsed" onClick={() => setCollapsed(false)}>
        <span className="thinking-icon">⋯</span>
      </div>
    );
  }

  return (
    <div className="thinking-bubble" onClick={() => setCollapsed(true)}>
      <span className="thinking-icon">⋯</span>
      <span className="thinking-text">{message.text}</span>
    </div>
  );
}
