import { useState } from "react";
export default function OptionsBubble({ msg, onOption }) {
  const [selected, setSelected] = useState(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackText, setFeedbackText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const click = (val) => {
    if (selected) return;

    // If "feedback" is clicked, show input field
    if (val === "feedback") {
      setShowFeedback(true);
      return;
    }

    setSelected(val);
    onOption(val);
  };

  const submitFeedback = () => {
    if (!feedbackText.trim() || submitting) return;
    setSubmitting(true);
    setSelected("feedback");
    onOption("feedback", feedbackText);
  };

  return (
    <div className="options-bubble">
      {msg.prompt && <div className="prompt-text">{msg.prompt}</div>}

      {!showFeedback ? (
        <div className="option-row">
          {msg.options.map(o => (
            <button key={o.value}
              className={`option-btn ${selected === o.value ? "selected" : ""}`}
              onClick={() => click(o.value)} disabled={!!selected}>
              {o.label}
            </button>
          ))}
        </div>
      ) : (
        <div className="feedback-input">
          <textarea
            placeholder="Enter your feedback..."
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            autoFocus
            rows={3}
            disabled={submitting}
          />
          <div className="feedback-buttons">
            <button
              onClick={submitFeedback}
              disabled={!feedbackText.trim() || submitting}
              className={submitting ? "submitting" : ""}
            >
              {submitting ? "Submitting..." : "Submit Feedback"}
            </button>
            <button onClick={() => setShowFeedback(false)} disabled={submitting}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
