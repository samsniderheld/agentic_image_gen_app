export default function TextBubble({ message }) {
  return (
    <div className={`text-bubble ${message.role}`}>
      <div className="text-content">{message.text}</div>
    </div>
  );
}
