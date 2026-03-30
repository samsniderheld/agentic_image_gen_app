const post = (path, body) =>
  fetch(`/api${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(r => r.json());

// Every response includes { ...data, messages: [...newMessages] }
export const generate      = (form)                 => post("/generate", form);
export const reviewInitial = (decision, new_prompt) => post("/review/initial", { decision, new_prompt });
export const critique      = (isRecritique = false) => post("/critique", { is_recritique: isRecritique });
export const reviewFixes   = (ids, customFixes = []) => post("/review/fixes", { approved_fix_ids: ids, custom_fixes: customFixes });
export const acceptFix     = (accepted)             => post("/fix/accept", { accepted });
