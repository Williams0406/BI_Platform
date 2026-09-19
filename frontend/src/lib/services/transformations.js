import api from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

function unwrap(response) {
  return response.data;
}

export async function listTransformations(workspaceId) {
  return unwrap(await api.get(API_ENDPOINTS.transformations.list, {
    params: workspaceId ? { workspace: workspaceId } : undefined,
  }));
}

export async function getTransformation(id) {
  return unwrap(await api.get(API_ENDPOINTS.transformations.detail(id)));
}

export async function createTransformation(payload) {
  return unwrap(await api.post(API_ENDPOINTS.transformations.list, payload));
}

export async function updateTransformation(id, payload) {
  return unwrap(await api.patch(API_ENDPOINTS.transformations.detail(id), payload));
}

export async function deleteTransformation(id) {
  await api.delete(API_ENDPOINTS.transformations.detail(id));
}

export async function previewTransformation(id, limit = 100) {
  return unwrap(await api.post(API_ENDPOINTS.transformations.preview(id), { limit }));
}

export async function runTransformation(id) {
  return unwrap(await api.post(API_ENDPOINTS.transformations.run(id)));
}
