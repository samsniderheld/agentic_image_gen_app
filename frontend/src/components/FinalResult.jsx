export default function FinalResult({ data, onAdvance }) {
  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '20px', textAlign: 'center' }}>
      <h2>Final Result</h2>
      <p>Your image has been successfully generated and refined!</p>

      <img
        src={data.final_url}
        alt="Final result"
        style={{ width: '100%', marginBottom: '20px', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}
      />

      <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
        <a
          href={data.final_url}
          download="final_image.png"
          style={{
            padding: '12px 30px',
            backgroundColor: '#28a745',
            color: 'white',
            textDecoration: 'none',
            borderRadius: '4px',
            fontSize: '16px'
          }}
        >
          ⬇ Download
        </a>
        <button
          onClick={() => onAdvance("idle", {})}
          style={{
            padding: '12px 30px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            fontSize: '16px',
            cursor: 'pointer'
          }}
        >
          ↺ Start Over
        </button>
      </div>
    </div>
  );
}
