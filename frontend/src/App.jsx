import { useState } from 'react';
import PromptForm from './components/PromptForm';
import CritiquePanel from './components/CritiquePanel';
import PatchReview from './components/PatchReview';
import FinalResult from './components/FinalResult';

function App() {
  const [state, setState] = useState({ stage: 'idle', data: {} });

  const handleAdvance = (stage, data) => {
    setState({ stage, data });
  };

  const renderStage = () => {
    switch (state.stage) {
      case 'idle':
        return <PromptForm onAdvance={handleAdvance} />;

      case 'generating':
        return (
          <div style={{ textAlign: 'center', padding: '100px 20px' }}>
            <h2>Generating Image & Running Critique...</h2>
            <p>Please wait while your image is being created and analyzed.</p>
            <p style={{ fontSize: '14px', color: '#666', marginTop: '20px' }}>
              This may take 30-60 seconds depending on complexity.
            </p>
          </div>
        );

      case 'awaiting_fix_review':
        return <CritiquePanel data={state.data} onAdvance={handleAdvance} />;

      case 'awaiting_patch_review':
        return <PatchReview data={state.data} onAdvance={handleAdvance} />;

      case 'done':
        return <FinalResult data={state.data} onAdvance={handleAdvance} />;

      default:
        return (
          <div style={{ textAlign: 'center', padding: '100px 20px' }}>
            <h2>Unknown State</h2>
            <button onClick={() => handleAdvance('idle', {})}>Start Over</button>
          </div>
        );
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#f5f5f5',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      {renderStage()}
    </div>
  );
}

export default App;
