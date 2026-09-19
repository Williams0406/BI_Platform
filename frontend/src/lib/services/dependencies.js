import api from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

function unwrap(response) {
  return response.data;
}

export async function listDependencies(workspaceId) {
  return unwrap(await api.get(API_ENDPOINTS.dependencies.edges, {
    params: workspaceId ? { workspace: workspaceId } : undefined,
  }));
}

export async function createDependency(payload) {
  return unwrap(await api.post(API_ENDPOINTS.dependencies.edges, payload));
}

export async function deleteDependency(id) {
  await api.delete(API_ENDPOINTS.dependencies.edgeDetail(id));
}

export async function listAssetStates() {
  return unwrap(await api.get(API_ENDPOINTS.dependencies.states));
}

export async function listChangeEvents() {
  return unwrap(await api.get(API_ENDPOINTS.dependencies.events));
}

export async function getLineage(assetId) {
  return unwrap(await api.get(API_ENDPOINTS.dependencies.lineage(assetId)));
}
