import { useState } from 'react';

export default function OptionsBubble({ message, onAction }) {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState('');

  const handleOptionClick = (value) => {
    if (value === 'feedback') {
      setShowFeedback(true);
    } else {
      onAction({ decision: value });
    }
  };

  const handleSubmitFeedback = () => {
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
            autoFocus
          />
          <div className="feedback-actions">
            <button className="feedback-submit" onClick={handleSubmitFeedback}>
              Submit
            </button>
            <button className="feedback-cancel" onClick={() => setShowFeedback(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
