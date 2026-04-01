import { useState } from "react";
import MessageList from "./chat/MessageList";
import InputBar    from "./chat/InputBar";
import * as api    from "./api";
import "./styles.css";

const WELCOME = { role: "agent", type: "text",
  content: "Hi! Let's create an image. First, choose your aspect ratio:" };

const ASPECT_RATIO_OPTIONS = { role: "agent", type: "options",
  prompt: "Select aspect ratio:",
  options: [
    { label: "1:1 Square", value: "1:1" },
    { label: "16:9 Landscape", value: "16:9" },
    { label: "9:16 Portrait", value: "9:16" },
    { label: "4:3 Standard", value: "4:3" }
  ]
};

export default function App() {
  const [messages,      setMessages]      = useState([WELCOME, ASPECT_RATIO_OPTIONS]);
  const [stage,         setStage]         = useState("selecting_aspect_ratio");
  const [aspectRatio,   setAspectRatio]   = useState("1:1");
  const [awaitingInput, setAwaitingInput] = useState(null);
  // awaitingInput: null | "edit"

  const working = ["generating", "critiquing", "applying_fixes"].includes(stage);

  const append = (newMsgs) => setMessages(m => [...m, ...(newMsgs || [])]);

  const handleSend = async (text, images = []) => {
    // Show user message with text and images
    const userMsg = { role: "user", type: "text", content: text || "(images attached)" };
    append([userMsg]);

    // Show image previews if any
    if (images.length > 0) {
      images.forEach(img => {
        append([{ role: "user", type: "image", url: img.data, caption: img.name }]);
      });
    }

    if (awaitingInput === "edit") {
      setAwaitingInput(null);
      setStage("generating");
      const res = await api.reviewInitial("edit", text);
      setStage(res.stage);
      append(res.messages);
      return;
    }

    // idle → generate (with optional images)
    setStage("generating");
    const res = await api.generate({
      prompt: text,
      aspect_ratio: aspectRatio,
      input_images: images.map(img => img.data)
    });
    setStage(res.stage);
    append(res.messages);
  };

  const handleOption = async (value, feedback = null) => {
    // Handle aspect ratio selection
    if (["1:1", "16:9", "9:16", "4:3"].includes(value)) {
      setAspectRatio(value);
      append([
        { role: "user", type: "text", content: `Selected ${value}` },
        { role: "agent", type: "text", content: "Great! Now describe what you'd like to generate." }
      ]);
      setStage("idle");
      return;
    }

    // Handle initial image review (after generation, before critique)
    if (stage === "awaiting_initial_review") {
      if (value === "accept") {
        setStage("critiquing");
        const res = await api.critique(false); // false = initial critique
        setStage(res.stage);
        append(res.messages);
        return;
      } else if (value === "reject") {
        setStage("idle");
        append([{ role: "agent", type: "text", content: "Let's start over. What would you like to generate?" }]);
        return;
      }
    }

    // Handle fixes review (after fixes applied, before finalization)
    if (stage === "awaiting_fixes_review") {
      if (value === "accept_all_fixes") {
        setStage("finalizing");
        const res = await api.acceptFix(true);
        setStage(res.stage);
        append(res.messages);
        return;
      } else if (value === "reject_all_fixes") {
        setStage("finalizing");
        const res = await api.acceptFix(false);
        setStage(res.stage);
        append(res.messages);
        return;
      } else if (value === "recritique") {
        handleRecritique();
        return;
      }
    }

    // Handle pipeline agent reviews with approve/feedback/reject
    // Extract agent name from stage (e.g., "awaiting_planner_review" → "planner")
    const agentMatch = stage.match(/^awaiting_(.+)_review$/);
    if (agentMatch) {
      const agentName = agentMatch[1];
      setStage("processing");
      const res = await api.reviewAgent(agentName, value, feedback);
      setStage(res.stage);
      append(res.messages);
      return;
    }

    // Handle other global actions
    if (value === "start_over") {
      setMessages([WELCOME, ASPECT_RATIO_OPTIONS]);
      setStage("selecting_aspect_ratio");
      setAspectRatio("1:1");
      setAwaitingInput(null);
    }
  };

  const handleChecklist = async (ids, customFixes = []) => {
    setStage("applying_fixes");
    const res = await api.reviewFixes(ids, customFixes);
    setStage(res.stage);
    append(res.messages);
  };

  const handleRecritique = async () => {
    setStage("running_critique");
    const res = await api.critique(true);  // true = is_recritique
    setStage(res.stage);
    append(res.messages);
  };

  const inputPlaceholder = awaitingInput
    ? "Enter your updated prompt..."
    : stage === "idle"
    ? "Describe what you'd like to generate..."
    : stage === "selecting_aspect_ratio"
    ? "Select an aspect ratio first..."
    : "Agent is working...";

  return (
    <div className="chat-shell">
      <MessageList
        messages={messages}
        working={working}
        onOption={handleOption}
        onChecklist={handleChecklist}
        onRecritique={handleRecritique}
      />
      <InputBar
        onSend={handleSend}
        disabled={(working && !awaitingInput) || stage === "selecting_aspect_ratio"}
        placeholder={inputPlaceholder}
      />
    </div>
  );
}
