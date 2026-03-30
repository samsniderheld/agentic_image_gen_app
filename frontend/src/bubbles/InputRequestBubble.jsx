export default function InputRequestBubble({ msg }) {
  return (
    <div className="input-request-bubble">
      ✏️ {msg.placeholder || "Type your response below ↓"}
    </div>
  );
}
