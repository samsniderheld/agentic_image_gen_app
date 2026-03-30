export default function TextBubble({ msg }) {
  return <div className={`bubble ${msg.role}`}>{msg.content}</div>;
}
