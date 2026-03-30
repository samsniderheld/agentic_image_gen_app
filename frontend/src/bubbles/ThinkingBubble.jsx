import { useState } from "react";
export default function ThinkingBubble({ msg }) {
  const [open, setOpen] = useState(false);
  const preview = msg.content.length > 60 ? msg.content.slice(0, 60) + "…" : msg.content;
  return (
    <div className="thinking-bubble" onClick={() => setOpen(o => !o)}>
      <div className="label">🧠 Thinking {open ? "▲" : "▼"}</div>
      {open ? msg.content : preview}
    </div>
  );
}
