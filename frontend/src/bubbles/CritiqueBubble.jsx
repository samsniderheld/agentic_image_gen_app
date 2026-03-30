export default function CritiqueBubble({ msg }) {
  const score = msg.score;
  const color = score >= 0.8 ? "var(--green)" : score >= 0.6 ? "var(--yellow)" : "var(--red)";
  return (
    <div className="critique-bubble">
      <div className="score-row">
        <span className="score-number" style={{ color }}>{(score * 100).toFixed(0)}</span>
        <span style={{ color, fontSize: "0.9rem" }}>/100</span>
        <span className={`score-badge ${msg.passed ? "badge-pass" : "badge-fail"}`}>
          {msg.passed ? "Passed ✓" : "Needs fixes ⚠"}
        </span>
      </div>
      <div className="score-bar-track">
        <div className="score-bar-fill" style={{ width: `${score * 100}%`, background: color }} />
      </div>
      <div className="assessment">{msg.assessment}</div>
    </div>
  );
}
