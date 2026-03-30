export default function ComparisonBubble({ msg }) {
  return (
    <div className="comparison-bubble">
      <div className="sides">
        <div className="side">
          <div className="side-label">Before</div>
          <img src={msg.leftUrl} alt="before" />
        </div>
        <div className="side">
          <div className="side-label">After</div>
          <img src={msg.rightUrl} alt="after" />
        </div>
      </div>
      {msg.caption && <div className="caption">{msg.caption}</div>}
    </div>
  );
}
