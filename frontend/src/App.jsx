import { useState } from "react";
import MessageList from "./chat/MessageList";
import InputBar    from "./chat/InputBar";
import * as api    from "./api";
import "./styles.css";

const WELCOME = { role: "agent", type: "text",
  content: "Hi! Describe what you'd like to generate, and I'll get started." };

export default function App() {
  const [messages,      setMessages]      = useState([WELCOME]);
  const [stage,         setStage]         = useState("idle");
  const [awaitingInput, setAwaitingInput] = useState(null);
  // awaitingInput: null | "edit"

  const working = ["generating", "critiquing", "applying_fixes"].includes(stage);

  const append = (newMsgs) => setMessages(m => [...m, ...(newMsgs || [])]);

  const handleSend = async (text) => {
    append([{ role: "user", type: "text", content: text }]);

    if (awaitingInput === "edit") {
      setAwaitingInput(null);
      setStage("generating");
      const res = await api.reviewInitial("edit", text);
      setStage(res.stage);
      append(res.messages);
      return;
    }

    // idle → generate
    setStage("generating");
    const res = await api.generate({ prompt: text, aspect_ratio: "1:1" });
    setStage(res.stage);
    append(res.messages);
  };

  const handleOption = async (value) => {
    if (value === "accept") {
      setStage("critiquing");
      const res = await api.reviewInitial("accept");
      setStage(res.stage);
      append(res.messages);
    } else if (value === "edit") {
      setAwaitingInput("edit");
      const res = await api.reviewInitial("edit");
      append(res.messages);
    } else if (value === "reject") {
      const res = await api.reviewInitial("reject");
      setStage("idle");
      append(res.messages);
    } else if (value === "accept_all_fixes") {
      setStage("finalizing");
      const res = await api.acceptFix(true);
      setStage(res.stage);
      append(res.messages);
    } else if (value === "reject_all_fixes") {
      setStage("finalizing");
      const res = await api.acceptFix(false);
      setStage(res.stage);
      append(res.messages);
    } else if (value === "start_over") {
      setMessages([WELCOME]);
      setStage("idle");
      setAwaitingInput(null);
    }
  };

  const handleChecklist = async (ids) => {
    setStage("applying_fixes");
    const res = await api.reviewFixes(ids);
    setStage(res.stage);
    append(res.messages);
  };

  const inputPlaceholder = awaitingInput
    ? "Enter your updated prompt..."
    : stage === "idle"
    ? "Describe what you'd like to generate..."
    : "Agent is working...";

  return (
    <div className="chat-shell">
      <MessageList
        messages={messages}
        working={working}
        onOption={handleOption}
        onChecklist={handleChecklist}
      />
      <InputBar
        onSend={handleSend}
        disabled={working && !awaitingInput}
        placeholder={inputPlaceholder}
      />
    </div>
  );
}
