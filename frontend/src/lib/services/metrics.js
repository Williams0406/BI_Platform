import api from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

function listParams(workspaceId) {
  return workspaceId ? { workspace: workspaceId } : undefined;
}

export async function listSemanticModels(workspaceId) {
  const response = await api.get(API_ENDPOINTS.metrics.semanticModels, { params: listParams(workspaceId) });
  return response.data;
}
export async function getSemanticModel(id) {
  const response = await api.get(API_ENDPOINTS.metrics.semanticModelDetail(id));
  return response.data;
}
export async function createSemanticModel(payload) {
  const response = await api.post(API_ENDPOINTS.metrics.semanticModels, payload);
  return response.data;
}
export async function updateSemanticModel(id, payload) {
  const response = await api.patch(API_ENDPOINTS.metrics.semanticModelDetail(id), payload);
  return response.data;
}
export async function deleteSemanticModel(id) {
  await api.delete(API_ENDPOINTS.metrics.semanticModelDetail(id));
}

export async function listDimensions(semanticModelId) {
  const response = await api.get(API_ENDPOINTS.metrics.dimensions, {
    params: semanticModelId ? { semantic_model: semanticModelId } : undefined,
  });
  return response.data;
}
export async function createDimension(payload) {
  const response = await api.post(API_ENDPOINTS.metrics.dimensions, payload);
  return response.data;
}
export async function updateDimension(id, payload) {
  const response = await api.patch(API_ENDPOINTS.metrics.dimensionDetail(id), payload);
  return response.data;
}
export async function deleteDimension(id) {
  await api.delete(API_ENDPOINTS.metrics.dimensionDetail(id));
}

export async function listMetrics(workspaceId) {
  const response = await api.get(API_ENDPOINTS.metrics.list, { params: listParams(workspaceId) });
  return response.data;
}
export async function getMetric(id) {
  const response = await api.get(API_ENDPOINTS.metrics.detail(id));
  return response.data;
}
export async function createMetric(payload) {
  const response = await api.post(API_ENDPOINTS.metrics.list, payload);
  return response.data;
}
export async function updateMetric(id, payload) {
  const response = await api.patch(API_ENDPOINTS.metrics.detail(id), payload);
  return response.data;
}
export async function deleteMetric(id) {
  await api.delete(API_ENDPOINTS.metrics.detail(id));
}
export async function queryMetric(id, payload) {
  const response = await api.post(API_ENDPOINTS.metrics.query(id), payload);
  return response.data;
}
