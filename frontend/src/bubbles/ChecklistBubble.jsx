import { useState } from "react";
export default function ChecklistBubble({ msg, onChecklist }) {
  const [checked, setChecked] = useState(
    Object.fromEntries(msg.items.map(i => [i.id, i.checked]))
  );
  const [submitted, setSubmitted] = useState(false);
  const [showCustomFixForm, setShowCustomFixForm] = useState(false);
  const [customFixes, setCustomFixes] = useState([]);
  const [customFixPrompt, setCustomFixPrompt] = useState("");

  const toggle = (id) => setChecked(c => ({ ...c, [id]: !c[id] }));

  const addCustomFix = () => {
    if (!customFixPrompt.trim()) return;

    const newFix = {
      id: `custom_${customFixes.length}`,
      label: customFixPrompt.trim(),
      severity: "medium"
    };

    setCustomFixes([...customFixes, newFix]);
    setChecked(c => ({ ...c, [newFix.id]: true }));
    setCustomFixPrompt("");
  };

  const removeCustomFix = (id) => {
    setCustomFixes(customFixes.filter(f => f.id !== id));
    setChecked(c => {
      const newChecked = { ...c };
      delete newChecked[id];
      return newChecked;
    });
  };

  const submit = () => {
    setSubmitted(true);
    const selectedIds = Object.entries(checked).filter(([,v]) => v).map(([k]) => k);
    onChecklist(selectedIds, customFixes);
  };

  const totalSelected = Object.values(checked).filter(Boolean).length;

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

      {customFixes.map(fix => (
        <label key={fix.id} className="checklist-item custom-fix-item">
          <input type="checkbox" checked={!!checked[fix.id]}
            onChange={() => toggle(fix.id)} disabled={submitted} />
          <span className={`severity-chip chip-${fix.severity}`}>CUSTOM</span>
          {fix.label}
          {!submitted && (
            <button
              className="remove-custom-fix-btn"
              onClick={(e) => {
                e.preventDefault();
                removeCustomFix(fix.id);
              }}
            >
              ✕
            </button>
          )}
        </label>
      ))}

      {!submitted && (
        <div className="custom-fix-section">
          <button
            className="toggle-custom-fix-btn"
            onClick={() => setShowCustomFixForm(!showCustomFixForm)}
          >
            {showCustomFixForm ? "− Hide Custom Fix" : "+ Add Custom Fix"}
          </button>

          {showCustomFixForm && (
            <div className="custom-fix-form">
              <textarea
                value={customFixPrompt}
                onChange={(e) => setCustomFixPrompt(e.target.value)}
                placeholder="Describe the custom fix you'd like to apply..."
                rows={3}
              />
              <button
                className="add-custom-fix-btn"
                onClick={addCustomFix}
                disabled={!customFixPrompt.trim()}
              >
                Add Fix
              </button>
            </div>
          )}
        </div>
      )}

      <div className="checklist-actions">
        <button className="apply-btn" onClick={submit} disabled={submitted}>
          {submitted
            ? "Applying…"
            : `Apply ${totalSelected} Selected Fix${totalSelected !== 1 ? 'es' : ''}`
          }
        </button>
        {!submitted && msg.allowRecritique && (
          <button
            className="recritique-btn"
            onClick={() => {
              setSubmitted(true);
              if (msg.onRecritique) msg.onRecritique();
            }}
          >
            🔄 Run Critique Again
          </button>
        )}
      </div>
    </div>
  );
}
