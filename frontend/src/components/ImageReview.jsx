import { useState } from 'react';
import { reviewInitial } from '../api';

export default function ImageReview({ data, onAdvance }) {
  const [editing, setEditing] = useState(false);
  const [newPrompt, setNewPrompt] = useState('');
  const [loading, setLoading] = useState(false);

  const handleAccept = async () => {
    setLoading(true);
    try {
      const res = await reviewInitial("accept");
      onAdvance("awaiting_fix_review", res);
    } catch (error) {
      console.error("Accept failed:", error);
      alert("Failed to process. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    setLoading(true);
    try {
      const res = await reviewInitial("reject");
      onAdvance("idle", res);
    } catch (error) {
      console.error("Reject failed:", error);
      alert("Failed to process. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = async () => {
    if (!editing) {
      setEditing(true);
      return;
    }

    if (!newPrompt.trim()) {
      alert("Please enter a new prompt");
      return;
    }

    setLoading(true);
    try {
      const res = await reviewInitial("edit", newPrompt);
      onAdvance("awaiting_initial_review", res);
      setEditing(false);
      setNewPrompt('');
    } catch (error) {
      console.error("Edit failed:", error);
      alert("Failed to regenerate. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      <h2>Review Generated Image</h2>
      <img
        src={data.image_url}
        alt="Generated"
        style={{ width: '100%', marginBottom: '20px', borderRadius: '8px' }}
      />

      {editing ? (
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '5px' }}>New Prompt:</label>
          <textarea
            value={newPrompt}
            onChange={(e) => setNewPrompt(e.target.value)}
            rows={4}
            style={{ width: '100%', padding: '8px', marginBottom: '10px' }}
            disabled={loading}
          />
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={handleEdit}
              disabled={loading}
              style={{
                padding: '10px 20px',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: loading ? 'not-allowed' : 'pointer'
              }}
            >
              {loading ? 'Regenerating...' : 'Regenerate'}
            </button>
            <button
              onClick={() => setEditing(false)}
              disabled={loading}
              style={{
                padding: '10px 20px',
                backgroundColor: '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: loading ? 'not-allowed' : 'pointer'
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handleAccept}
            disabled={loading}
            style={{
              padding: '10px 20px',
              backgroundColor: '#28a745',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            ✓ Accept
          </button>
          <button
            onClick={handleReject}
            disabled={loading}
            style={{
              padding: '10px 20px',
              backgroundColor: '#dc3545',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            ✕ Reject
          </button>
          <button
            onClick={handleEdit}
            disabled={loading}
            style={{
              padding: '10px 20px',
              backgroundColor: '#ffc107',
              color: '#000',
              border: 'none',
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            ✎ Edit
          </button>
        </div>
      )}
    </div>
  );
}
