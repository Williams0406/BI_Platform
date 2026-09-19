const ACTIVE_WORKSPACE_KEY = "bi_active_workspace_id";

export function getStoredWorkspaceId() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACTIVE_WORKSPACE_KEY);
}

export function storeWorkspaceId(workspaceId) {
  if (typeof window === "undefined") return;
  if (!workspaceId) {
    window.localStorage.removeItem(ACTIVE_WORKSPACE_KEY);
    return;
  }
  window.localStorage.setItem(ACTIVE_WORKSPACE_KEY, workspaceId);
}

export function clearStoredWorkspaceId() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACTIVE_WORKSPACE_KEY);
}
