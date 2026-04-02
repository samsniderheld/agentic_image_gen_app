import { useState } from 'react';

export default function OptionsBubble({ message, onAction, disabled }) {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState('');

  const handleOptionClick = (value) => {
    if (disabled) return;
    if (value === 'feedback') {
      setShowFeedback(true);
    } else {
      onAction({ decision: value });
    }
  };

  const handleSubmitFeedback = () => {
    if (disabled) return;
    if (feedback.trim()) {
      onAction({ decision: 'feedback', feedback: feedback.trim() });
      setFeedback('');
      setShowFeedback(false);
    }
  };

  return (
    <div className="options-bubble">
      <div className="options-buttons">
        {message.options.map((option, idx) => (
          <button
            key={idx}
            className="option-button"
            onClick={() => handleOptionClick(option.value)}
            disabled={disabled}
          >
            {option.label}
          </button>
        ))}
      </div>

      {showFeedback && (
        <div className="feedback-form">
          <textarea
            className="feedback-textarea"
            placeholder="Enter your feedback..."
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            disabled={disabled}
            autoFocus
          />
          <div className="feedback-actions">
            <button className="feedback-submit" onClick={handleSubmitFeedback} disabled={disabled}>
              Submit
            </button>
            <button className="feedback-cancel" onClick={() => setShowFeedback(false)} disabled={disabled}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
