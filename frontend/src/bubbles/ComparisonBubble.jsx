export default function ComparisonBubble({ message }) {
  return (
    <div className="comparison-bubble">
      <div className="comparison-grid">
        <div className="comparison-item">
          <div className="comparison-label">{message.beforeLabel}</div>
          <img src={message.before} alt={message.beforeLabel} />
        </div>
        <div className="comparison-item">
          <div className="comparison-label">{message.afterLabel}</div>
          <img src={message.after} alt={message.afterLabel} />
        </div>
      </div>
    </div>
  );
}
