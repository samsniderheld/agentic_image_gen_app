import { useState, useEffect } from 'react';
import { reviewFixes } from '../api';

export default function CritiquePanel({ data, onAdvance }) {
  const { critique, annotated_url, image_url, input_image_urls } = data;
  const [checkedFixes, setCheckedFixes] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [showAnnotated, setShowAnnotated] = useState(true);

  // Custom fix form state
  const [showCustomFixForm, setShowCustomFixForm] = useState(false);
  const [customFixes, setCustomFixes] = useState([]);
  const [customFixPrompt, setCustomFixPrompt] = useState('');

  useEffect(() => {
    // Auto-check high and medium severity fixes
    const autoChecked = new Set(
      critique.fixes_required
        .filter(f => f.severity === 'high' || f.severity === 'medium')
        .map(f => f.region_id)
    );
    setCheckedFixes(autoChecked);
  }, [critique]);

  const toggleFix = (regionId) => {
    setCheckedFixes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(regionId)) {
        newSet.delete(regionId);
      } else {
        newSet.add(regionId);
      }
      return newSet;
    });
  };

  const handleFinish = async () => {
    setLoading(true);
    try {
      // If threshold met and user clicks finish, send empty array
      const res = await reviewFixes([]);
      onAdvance(res.stage, res);
    } catch (error) {
      console.error("Finish failed:", error);
      alert("Failed to finish. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleApplyFixes = async () => {
    setLoading(true);
    try {
      // Combine AI-detected fixes and custom fixes
      const aiFixIds = Array.from(checkedFixes).filter(id => !id.startsWith('custom_'));
      const customFixIds = customFixes.map(f => f.region_id);
      const allFixIds = [...aiFixIds, ...customFixIds];

      // If there are custom fixes, we need to add them to the backend
      // For now, we'll send just the IDs and handle custom fixes separately
      const res = await reviewFixes(allFixIds);

      // Store custom fixes in the response data if needed
      if (customFixes.length > 0) {
        res.customFixes = customFixes;
      }

      onAdvance(res.stage, res);
    } catch (error) {
      console.error("Apply fixes failed:", error);
      alert("Failed to apply fixes. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 0.8) return '#28a745';
    if (score >= 0.6) return '#ffc107';
    return '#dc3545';
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'high': return '#dc3545';
      case 'medium': return '#ffa500';
      case 'low': return '#ffff00';
      default: return '#000';
    }
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '20px' }}>
      <h2>Image Critique</h2>

      {/* Input Images Section (if any) */}
      {input_image_urls && input_image_urls.length > 0 && (
        <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
          <h3 style={{ marginTop: 0 }}>Input Images Used</h3>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {input_image_urls.map((url, idx) => (
              <img
                key={idx}
                src={url}
                alt={`Input ${idx + 1}`}
                style={{ width: '120px', height: '120px', objectFit: 'cover', borderRadius: '4px', border: '2px solid #ccc' }}
              />
            ))}
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '20px', marginBottom: '20px' }}>
        {/* Original Generated Image */}
        <div>
          <h3>Generated Image</h3>
          <img
            src={image_url}
            alt="Generated"
            style={{ width: '100%', borderRadius: '8px', border: '2px solid #28a745' }}
          />
        </div>

        {/* Annotated Image with Issues */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <h3 style={{ margin: 0 }}>Issues Identified</h3>
            <button
              onClick={() => setShowAnnotated(!showAnnotated)}
              style={{
                padding: '5px 10px',
                fontSize: '12px',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              {showAnnotated ? 'Hide' : 'Show'} Annotations
            </button>
          </div>
          <img
            src={showAnnotated ? annotated_url : image_url}
            alt={showAnnotated ? "Annotated" : "Original"}
            style={{ width: '100%', borderRadius: '8px', border: showAnnotated ? '2px solid #ffc107' : '2px solid #28a745' }}
          />
        </div>

        {/* Critique Details */}
        <div>
          <div style={{
            padding: '15px',
            backgroundColor: getScoreColor(critique.overall_score),
            color: 'white',
            borderRadius: '8px',
            marginBottom: '15px'
          }}>
            <h3 style={{ margin: '0 0 10px 0' }}>
              Score: {(critique.overall_score * 100).toFixed(0)}%
            </h3>
            <p style={{ margin: 0 }}>{critique.overall_assessment}</p>
          </div>

          {critique.image_integrations && critique.image_integrations.length > 0 && (
            <div style={{
              padding: '15px',
              backgroundColor: '#f8f9fa',
              borderRadius: '8px',
              marginBottom: '15px'
            }}>
              <h3 style={{ marginTop: 0 }}>Image Integration Analysis</h3>
              {critique.image_integrations.map((integration, idx) => (
                <div
                  key={idx}
                  style={{
                    marginBottom: '10px',
                    padding: '10px',
                    backgroundColor: 'white',
                    borderRadius: '4px',
                    borderLeft: `4px solid ${getScoreColor(integration.integration_score)}`
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                    <strong>Input Image {integration.image_index + 1}</strong>
                    <span style={{
                      padding: '2px 8px',
                      backgroundColor: getScoreColor(integration.integration_score),
                      color: 'white',
                      borderRadius: '3px',
                      fontSize: '12px'
                    }}>
                      {(integration.integration_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p style={{ margin: 0, fontSize: '14px', color: '#666' }}>
                    {integration.integration_notes}
                  </p>
                </div>
              ))}
            </div>
          )}

          {critique.fixes_required.length > 0 && (
            <div>
              <h3>Identified Issues</h3>
              <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                {critique.fixes_required.map(fix => (
                  <div
                    key={fix.region_id}
                    style={{
                      padding: '10px',
                      marginBottom: '10px',
                      border: `2px solid ${getSeverityColor(fix.severity)}`,
                      borderRadius: '4px',
                      backgroundColor: '#f8f9fa'
                    }}
                  >
                    <label style={{ display: 'flex', alignItems: 'start', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={checkedFixes.has(fix.region_id)}
                        onChange={() => toggleFix(fix.region_id)}
                        style={{ marginRight: '10px', marginTop: '3px' }}
                        disabled={loading}
                      />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>
                          {fix.region_id}
                          <span style={{
                            marginLeft: '10px',
                            padding: '2px 8px',
                            backgroundColor: getSeverityColor(fix.severity),
                            color: fix.severity === 'low' ? '#000' : '#fff',
                            borderRadius: '3px',
                            fontSize: '12px'
                          }}>
                            {fix.severity}
                          </span>
                        </div>
                        <div style={{ fontSize: '14px', marginBottom: '5px' }}>
                          {fix.issue_description}
                        </div>
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          Fix: {fix.fix_prompt}
                        </div>
                      </div>
                    </label>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Custom Fix Form */}
          <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#fff', borderRadius: '8px', border: '2px dashed #007bff' }}>
            <h4 style={{ marginTop: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Add Custom Fix</span>
              <button
                type="button"
                onClick={() => setShowCustomFixForm(!showCustomFixForm)}
                style={{
                  padding: '5px 10px',
                  fontSize: '12px',
                  backgroundColor: '#007bff',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                {showCustomFixForm ? 'Hide' : 'Show'} Form
              </button>
            </h4>

            {showCustomFixForm && (
              <div style={{ marginTop: '10px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px' }}>
                  Describe what you want to fix or change:
                </label>
                <textarea
                  value={customFixPrompt}
                  onChange={(e) => setCustomFixPrompt(e.target.value)}
                  rows={2}
                  placeholder="E.g., 'Brighten the sky in the top half' or 'Remove the object in the bottom right corner'"
                  style={{ width: '100%', padding: '8px', fontSize: '14px', marginBottom: '10px' }}
                />
                <button
                  type="button"
                  onClick={() => {
                    if (customFixPrompt.trim()) {
                      const newFix = {
                        region_id: `custom_${customFixes.length}`,
                        bbox: [0, 0, 100, 100], // Placeholder - will apply to whole image
                        severity: 'medium',
                        issue_description: 'Custom user-requested change',
                        fix_prompt: customFixPrompt.trim()
                      };
                      setCustomFixes([...customFixes, newFix]);
                      setCheckedFixes(new Set([...checkedFixes, newFix.region_id]));
                      setCustomFixPrompt('');
                    }
                  }}
                  disabled={!customFixPrompt.trim()}
                  style={{
                    padding: '8px 15px',
                    backgroundColor: customFixPrompt.trim() ? '#28a745' : '#ccc',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: customFixPrompt.trim() ? 'pointer' : 'not-allowed',
                    fontSize: '14px'
                  }}
                >
                  + Add Custom Fix
                </button>
              </div>
            )}

            {/* Display custom fixes */}
            {customFixes.length > 0 && (
              <div style={{ marginTop: '15px' }}>
                <strong style={{ fontSize: '14px' }}>Custom Fixes ({customFixes.length}):</strong>
                {customFixes.map((fix, idx) => (
                  <div
                    key={fix.region_id}
                    style={{
                      marginTop: '10px',
                      padding: '10px',
                      backgroundColor: '#e7f3ff',
                      borderRadius: '4px',
                      border: '1px solid #007bff'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ flex: 1 }}>
                        <strong style={{ fontSize: '12px', color: '#007bff' }}>Custom Fix {idx + 1}</strong>
                        <p style={{ margin: '5px 0 0 0', fontSize: '14px' }}>{fix.fix_prompt}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setCustomFixes(customFixes.filter((_, i) => i !== idx));
                          const newChecked = new Set(checkedFixes);
                          newChecked.delete(fix.region_id);
                          setCheckedFixes(newChecked);
                        }}
                        style={{
                          padding: '5px 10px',
                          backgroundColor: '#dc3545',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '12px'
                        }}
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div style={{ marginTop: '20px' }}>
            {critique.pass_threshold_met && (
              <button
                onClick={handleFinish}
                disabled={loading}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  marginRight: '10px'
                }}
              >
                ✓ Looks Good - Finish
              </button>
            )}
            <button
              onClick={handleApplyFixes}
              disabled={loading || (checkedFixes.size === 0 && customFixes.length === 0)}
              style={{
                padding: '10px 20px',
                backgroundColor: (checkedFixes.size === 0 && customFixes.length === 0) ? '#ccc' : '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: loading || (checkedFixes.size === 0 && customFixes.length === 0) ? 'not-allowed' : 'pointer'
              }}
            >
              Apply Fixes ({checkedFixes.size + customFixes.length})
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
