import { useState } from "react";
export default function OptionsBubble({ msg, onOption }) {
  const [selected, setSelected] = useState(null);
  const click = (val) => {
    if (selected) return;
    setSelected(val);
    onOption(val);
  };
  return (
    <div className="options-bubble">
      {msg.prompt && <div className="prompt-text">{msg.prompt}</div>}
      <div className="option-row">
        {msg.options.map(o => (
          <button key={o.value}
            className={`option-btn ${selected === o.value ? "selected" : ""}`}
            onClick={() => click(o.value)} disabled={!!selected}>
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}
