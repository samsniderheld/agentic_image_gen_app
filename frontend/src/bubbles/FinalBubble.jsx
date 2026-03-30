export default function FinalBubble({ msg, onOption }) {
  return (
    <div className="final-bubble">
      <img src={msg.url} alt="final result" />
      {msg.caption && <div className="caption">{msg.caption}</div>}
      <div className="final-actions">
        <a className="final-btn download" href={msg.url} download="final.png">⬇ Download</a>
        <button className="final-btn start-over" onClick={() => onOption("start_over")}>
          ↺ Start Over
        </button>
      </div>
    </div>
  );
}
