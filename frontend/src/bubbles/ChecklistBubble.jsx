import { useState } from 'react';

export default function ChecklistBubble({ message, onAction, disabled }) {
  const [selectedFixes, setSelectedFixes] = useState(
    message.fixes
      .filter((f) => f.severity === 'high' || f.severity === 'medium')
      .map((f) => f.fix_id)
  );
  const [customFixes, setCustomFixes] = useState(['']);

  const toggleFix = (fixId) => {
    setSelectedFixes((prev) =>
      prev.includes(fixId) ? prev.filter((id) => id !== fixId) : [...prev, fixId]
    );
  };

  const addCustomFix = () => {
    setCustomFixes([...customFixes, '']);
  };

  const updateCustomFix = (idx, value) => {
    const updated = [...customFixes];
    updated[idx] = value;
    setCustomFixes(updated);
  };

  const removeCustomFix = (idx) => {
    setCustomFixes(customFixes.filter((_, i) => i !== idx));
  };

  const handleApply = () => {
    const custom = customFixes.filter((f) => f.trim());
    const payload = {
      approved_fix_ids: selectedFixes,
      custom_fixes: custom,
    };
    console.log('ChecklistBubble sending payload:', payload);
    onAction(payload);
  };

  const severityColor = (severity) => {
    if (severity === 'high') return '#ff4444';
    if (severity === 'medium') return '#ffaa00';
    return '#888';
  };

  return (
    <div className="checklist-bubble">
      <div className="checklist-header">Select fixes to apply:</div>

      <div className="checklist-items">
        {message.fixes.map((fix) => (
          <div key={fix.fix_id} className="checklist-item">
            <label className="checklist-label">
              <input
                type="checkbox"
                checked={selectedFixes.includes(fix.fix_id)}
                onChange={() => toggleFix(fix.fix_id)}
              />
              <span className="checklist-text">
                <span
                  className="severity-chip"
                  style={{ backgroundColor: severityColor(fix.severity) }}
                >
                  {fix.severity}
                </span>
                {fix.issue_description}
              </span>
            </label>
          </div>
        ))}
      </div>

      {message.allowCustom && (
        <div className="custom-fixes">
          <div className="custom-fixes-header">Custom fixes:</div>
          {customFixes.map((fix, idx) => (
            <div key={idx} className="custom-fix-row">
              <input
                type="text"
                className="custom-fix-input"
                placeholder="Describe a fix..."
                value={fix}
                onChange={(e) => updateCustomFix(idx, e.target.value)}
              />
              <button
                className="custom-fix-remove"
                onClick={() => removeCustomFix(idx)}
              >
                ✕
              </button>
            </div>
          ))}
          <button className="custom-fix-add" onClick={addCustomFix}>
            + Add custom fix
          </button>
        </div>
      )}

      <div className="checklist-actions">
        <button className="checklist-apply" onClick={handleApply} disabled={disabled}>
          Apply Selected Fixes
        </button>
        {message.allowRecritique && (
          <button
            className="checklist-recritique"
            onClick={() => onAction({ action: 'critique' })}
            disabled={disabled}
          >
            Re-critique
          </button>
        )}
      </div>
    </div>
  );
}
