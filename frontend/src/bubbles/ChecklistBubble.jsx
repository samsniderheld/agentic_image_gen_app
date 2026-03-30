import { useState } from "react";
export default function ChecklistBubble({ msg, onChecklist }) {
  const [checked, setChecked] = useState(
    Object.fromEntries(msg.items.map(i => [i.id, i.checked]))
  );
  const [submitted, setSubmitted] = useState(false);

  const toggle = (id) => setChecked(c => ({ ...c, [id]: !c[id] }));
  const submit = () => {
    setSubmitted(true);
    onChecklist(Object.entries(checked).filter(([,v]) => v).map(([k]) => k));
  };

  return (
    <div className="checklist-bubble">
      <div className="prompt-text">{msg.prompt}</div>
      {msg.items.map(item => (
        <label key={item.id} className="checklist-item">
          <input type="checkbox" checked={!!checked[item.id]}
            onChange={() => toggle(item.id)} disabled={submitted} />
          <span className={`severity-chip chip-${item.severity}`}>{item.severity}</span>
          {item.label}
        </label>
      ))}
      <button className="apply-btn" onClick={submit} disabled={submitted}>
        {submitted ? "Applying…" : "Apply Selected Fixes"}
      </button>
    </div>
  );
}
