import TextBubble from '../bubbles/TextBubble';
import ThinkingBubble from '../bubbles/ThinkingBubble';
import ImageBubble from '../bubbles/ImageBubble';
import VideoBubble from '../bubbles/VideoBubble';
import ComparisonBubble from '../bubbles/ComparisonBubble';
import OptionsBubble from '../bubbles/OptionsBubble';
import ChecklistBubble from '../bubbles/ChecklistBubble';
import CritiqueBubble from '../bubbles/CritiqueBubble';
import FinalBubble from '../bubbles/FinalBubble';

export default function Message({ message, onAction, working }) {
  switch (message.type) {
    case 'text':
      return <TextBubble message={message} />;
    case 'thinking':
      return <ThinkingBubble message={message} />;
    case 'image':
      return <ImageBubble message={message} />;
    case 'video':
      return <VideoBubble message={message} />;
    case 'comparison':
      return <ComparisonBubble message={message} />;
    case 'options':
      return <OptionsBubble message={message} onAction={onAction} disabled={working} />;
    case 'checklist':
      return <ChecklistBubble message={message} onAction={onAction} disabled={working} />;
    case 'critique':
      return <CritiqueBubble message={message} />;
    case 'final':
      return <FinalBubble message={message} onAction={onAction} disabled={working} />;
    default:
      return <div>Unknown message type: {message.type}</div>;
  }
}
