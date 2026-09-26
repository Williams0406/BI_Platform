const PREFIX = "bi-code-drafts:";
export function readCodeDrafts(workspace) {
  if (!workspace || typeof window === "undefined") return [];
  try {
    const drafts=JSON.parse(localStorage.getItem(PREFIX + workspace) || "[]");
    return Array.isArray(drafts)?drafts.filter(item=>item?.id&&typeof item.code==="string"):[];
  } catch { return []; }
}
export function writeCodeDraft(workspace, id, patch) {
  if (!workspace || !id) return;
  const drafts = readCodeDrafts(workspace).filter(item => item.id !== id);
  if (patch?.code?.trim()) drafts.push({id, ...patch});
  localStorage.setItem(PREFIX + workspace, JSON.stringify(drafts));
  window.dispatchEvent(new Event("bi-code-drafts-changed"));
}
