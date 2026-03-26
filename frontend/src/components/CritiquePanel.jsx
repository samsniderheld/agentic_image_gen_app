import { useState, useEffect } from 'react';
import { reviewFixes } from '../api';

export default function CritiquePanel({ data, onAdvance }) {
  const { critique, annotated_url, image_url, input_image_urls } = data;
  const [checkedFixes, setCheckedFixes] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [showAnnotated, setShowAnnotated] = useState(true);

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
      const res = await reviewFixes(Array.from(checkedFixes));
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
            {critique.fixes_required.length > 0 && (
              <button
                onClick={handleApplyFixes}
                disabled={loading || checkedFixes.size === 0}
                style={{
                  padding: '10px 20px',
                  backgroundColor: checkedFixes.size === 0 ? '#ccc' : '#007bff',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: loading || checkedFixes.size === 0 ? 'not-allowed' : 'pointer'
                }}
              >
                Apply Selected Fixes ({checkedFixes.size})
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
