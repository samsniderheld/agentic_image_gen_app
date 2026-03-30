export default function ImageBubble({ msg }) {
  return (
    <div className="image-bubble">
      <img src={msg.url} alt={msg.caption} onClick={() => window.open(msg.url, "_blank")} />
      {msg.caption && <div className="caption">{msg.caption}</div>}
    </div>
  );
}
