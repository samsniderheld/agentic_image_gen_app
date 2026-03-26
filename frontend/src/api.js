const post = (path, body) =>
  fetch(`/api${path}`, { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body) }).then(r => r.json());

export const generate = (form) => post("/generate", form);
export const reviewInitial = (decision, new_prompt = null) => post("/review/initial", { decision, new_prompt });
export const reviewFixes = (approved_fix_ids) => post("/review/fixes", { approved_fix_ids });
export const acceptFix = (accepted) => post("/fix/accept", { accepted });
