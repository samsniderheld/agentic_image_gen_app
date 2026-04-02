import { useEffect, useRef } from 'react';
import Message from './Message';

export default function MessageList({ messages, onAction }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="message-list">
      {messages.map((msg, idx) => (
        <div key={idx} className="message-wrapper">
          <Message message={msg} onAction={onAction} />
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}
