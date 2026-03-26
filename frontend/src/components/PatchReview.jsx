import { useState } from 'react';
import { acceptFix } from '../api';

export default function PatchReview({ data, onAdvance }) {
  const [loading, setLoading] = useState(false);

  const handleAccept = async () => {
    setLoading(true);
    try {
      const res = await acceptFix(true);
      onAdvance(res.stage, res);
    } catch (error) {
      console.error("Accept fix failed:", error);
      alert("Failed to accept fix. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleSkip = async () => {
    setLoading(true);
    try {
      const res = await acceptFix(false);
      onAdvance(res.stage, res);
    } catch (error) {
      console.error("Skip fix failed:", error);
      alert("Failed to skip fix. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '20px' }}>
      <h2>Review Fix {data.fix_index + 1} of {data.total_fixes}</h2>

      <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
        <h3 style={{ marginTop: 0 }}>Issue:</h3>
        <p>{data.fix.issue_description}</p>
        <h4>Fix Applied:</h4>
        <p style={{ fontStyle: 'italic', color: '#666' }}>{data.fix.fix_prompt}</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
        <div>
          <h3>Original</h3>
          <img
            src={data.original_url}
            alt="Original region"
            style={{ width: '100%', border: '2px solid #ccc', borderRadius: '8px' }}
          />
        </div>
        <div>
          <h3>Fixed</h3>
          <img
            src={data.patch_url}
            alt="Fixed region"
            style={{ width: '100%', border: '2px solid #28a745', borderRadius: '8px' }}
          />
        </div>
      </div>

      <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
        <button
          onClick={handleAccept}
          disabled={loading}
          style={{
            padding: '12px 30px',
            backgroundColor: '#28a745',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            fontSize: '16px',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          ✓ Accept Fix
        </button>
        <button
          onClick={handleSkip}
          disabled={loading}
          style={{
            padding: '12px 30px',
            backgroundColor: '#6c757d',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            fontSize: '16px',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          ✕ Skip
        </button>
      </div>
    </div>
  );
}
