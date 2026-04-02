import { useState, useEffect } from 'react';
import MessageList from './chat/MessageList';
import InputBar from './chat/InputBar';
import { action } from './api';
import './styles.css';

export default function App() {
  const [messages, setMessages] = useState([]);
  const [stage, setStage] = useState('idle');
  const [aspectRatio, setAspectRatio] = useState('1:1');
  const [working, setWorking] = useState(false);

  useEffect(() => {
    // Show welcome message and aspect ratio selector
    setMessages([
      {
        type: 'text',
        role: 'agent',
        text: 'Welcome to the Agentic Image Generator! Select an aspect ratio to begin:',
      },
      {
        type: 'options',
        options: [
          { label: '1:1 Square', value: '1:1' },
          { label: '16:9 Landscape', value: '16:9' },
          { label: '9:16 Portrait', value: '9:16' },
          { label: '4:3 Classic', value: '4:3' },
        ],
        showFeedback: false,
      },
    ]);
  }, []);

  const handleAction = async (payload) => {
    if (working) return;

    setWorking(true);
    try {
      const result = await action({ action: 'review', ...payload });
      setMessages(result.messages);
      // Update stage if needed (could be derived from messages)
    } catch (error) {
      console.error('Action failed:', error);
      setMessages((prev) => [
        ...prev,
        {
          type: 'text',
          role: 'agent',
          text: `Error: ${error.message}`,
        },
      ]);
    } finally {
      setWorking(false);
    }
  };

  const handleSend = async ({ text, images }) => {
    if (working) return;

    // If we're at the aspect ratio selection stage
    if (stage === 'idle' && messages.length === 2) {
      // This shouldn't happen via InputBar, but handle it anyway
      return;
    }

    setWorking(true);
    try {
      const result = await action({
        action: 'generate',
        prompt: text,
        aspect_ratio: aspectRatio,
        images: images,
      });
      setMessages(result.messages);
      setStage('running');
    } catch (error) {
      console.error('Generate failed:', error);
      setMessages((prev) => [
        ...prev,
        {
          type: 'text',
          role: 'agent',
          text: `Error: ${error.message}`,
        },
      ]);
    } finally {
      setWorking(false);
    }
  };

  const handleOptionClick = async (option) => {
    if (working) return;

    // Handle aspect ratio selection
    if (stage === 'idle' && ['1:1', '16:9', '9:16', '4:3'].includes(option.decision)) {
      setAspectRatio(option.decision);
      setStage('ready');
      setMessages((prev) => [
        ...prev,
        {
          type: 'text',
          role: 'agent',
          text: `Aspect ratio set to ${option.decision}. What would you like to create?`,
        },
      ]);
      return;
    }

    // Handle critique action
    if (option.decision === 'critique') {
      setWorking(true);
      try {
        const result = await action({ action: 'critique' });
        setMessages(result.messages);
      } catch (error) {
        console.error('Critique failed:', error);
      } finally {
        setWorking(false);
      }
      return;
    }

    // Handle apply fixes
    if (option.approved_fix_ids !== undefined) {
      setWorking(true);
      try {
        const result = await action({ action: 'apply_fixes', ...option });
        setMessages(result.messages);
      } catch (error) {
        console.error('Apply fixes failed:', error);
      } finally {
        setWorking(false);
      }
      return;
    }

    // Handle accept/reject/recritique after fixes
    if (['accept', 'reject', 'recritique'].includes(option.decision)) {
      setWorking(true);
      try {
        const result = await action({ action: 'accept_fix', decision: option.decision });
        setMessages(result.messages);
      } catch (error) {
        console.error('Accept fix failed:', error);
      } finally {
        setWorking(false);
      }
      return;
    }

    // Handle generic review decisions
    handleAction(option);
  };

  return (
    <div className="app">
      <div className="chat-container">
        <MessageList messages={messages} onAction={handleOptionClick} />
        <InputBar onSend={handleSend} disabled={working} stage={stage} />
      </div>
    </div>
  );
}
