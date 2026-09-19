import api from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

function unwrap(response) {
  return response.data;
}

export async function listExecutions({ workspace, status, objectType } = {}) {
  const params = {};
  if (workspace) params.workspace = workspace;
  if (status) params.status = status;
  if (objectType) params.object_type = objectType;
  return unwrap(await api.get(API_ENDPOINTS.executions.list, { params }));
}

export async function getExecution(id) {
  return unwrap(await api.get(API_ENDPOINTS.executions.detail(id)));
}

export async function cancelExecution(id) {
  return unwrap(await api.post(API_ENDPOINTS.executions.cancel(id)));
}

export async function listExecutionEvents(id, after) {
  const params = {};
  if (after !== undefined && after !== null) params.after = after;
  return unwrap(await api.get(API_ENDPOINTS.executions.events(id), { params }));
}
