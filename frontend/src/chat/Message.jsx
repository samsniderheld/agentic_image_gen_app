import TextBubble        from "../bubbles/TextBubble";
import ThinkingBubble    from "../bubbles/ThinkingBubble";
import ImageBubble       from "../bubbles/ImageBubble";
import ComparisonBubble  from "../bubbles/ComparisonBubble";
import OptionsBubble     from "../bubbles/OptionsBubble";
import ChecklistBubble   from "../bubbles/ChecklistBubble";
import CritiqueBubble    from "../bubbles/CritiqueBubble";
import InputRequestBubble from "../bubbles/InputRequestBubble";
import FinalBubble       from "../bubbles/FinalBubble";

export default function Message({ msg, onOption, onChecklist, onRecritique }) {
  switch (msg.type) {
    case "text":         return <TextBubble msg={msg} />;
    case "thinking":     return <ThinkingBubble msg={msg} />;
    case "image":        return <ImageBubble msg={msg} />;
    case "comparison":   return <ComparisonBubble msg={msg} />;
    case "options":      return <OptionsBubble msg={msg} onOption={onOption} />;
    case "checklist":    return <ChecklistBubble msg={{...msg, onRecritique}} onChecklist={onChecklist} />;
    case "critique":     return <CritiqueBubble msg={msg} />;
    case "input_request":return <InputRequestBubble msg={msg} />;
    case "final":        return <FinalBubble msg={msg} onOption={onOption} />;
    default:             return null;
  }
}
