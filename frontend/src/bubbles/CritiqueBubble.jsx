export default function CritiqueBubble({ message }) {
  const scoreColor = (score) => {
    if (score >= 80) return '#22c55e';
    if (score >= 60) return '#eab308';
    return '#ef4444';
  };

  return (
    <div className="critique-bubble">
      <div className="critique-header">
        <div className="critique-score">
          <div className="score-label">Score</div>
          <div
            className="score-value"
            style={{ color: scoreColor(message.score) }}
          >
            {message.score}
          </div>
        </div>
        <div className={`critique-badge ${message.pass ? 'pass' : 'fail'}`}>
          {message.pass ? 'PASS' : 'FAIL'}
        </div>
      </div>

      <div className="critique-bar">
        <div
          className="critique-bar-fill"
          style={{
            width: `${message.score}%`,
            backgroundColor: scoreColor(message.score),
          }}
        />
      </div>

      <div className="critique-assessment">{message.assessment}</div>
    </div>
  );
}
