import { useEffect, useRef } from "react";
import Message from "./Message";

export default function MessageList({ messages, working, onOption, onChecklist, onRecritique }) {
  const bottomRef = useRef(null);
  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), [messages]);

  return (
    <div className="message-list">
      {messages.map((msg, i) => (
        <Message key={i} msg={msg} onOption={onOption} onChecklist={onChecklist} onRecritique={onRecritique} />
      ))}
      {working && (
        <div className="typing-indicator">
          <span/><span/><span/>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
