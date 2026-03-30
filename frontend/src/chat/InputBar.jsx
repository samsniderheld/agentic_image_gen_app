import { useState, useRef } from "react";

export default function InputBar({ onSend, disabled, placeholder }) {
  const [text, setText] = useState("");
  const ref = useRef(null);

  const submit = () => {
    const val = text.trim();
    if (!val || disabled) return;
    setText("");
    ref.current.style.height = "auto";
    onSend(val);
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
  };

  const onInput = (e) => {
    setText(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = e.target.scrollHeight + "px";
  };

  return (
    <div className="input-bar">
      <textarea ref={ref} value={text} onInput={onInput} onKeyDown={onKey}
        placeholder={placeholder} disabled={disabled} rows={1} />
      <button className="send-btn" onClick={submit} disabled={disabled || !text.trim()}>↑</button>
    </div>
  );
}
