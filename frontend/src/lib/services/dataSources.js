import api from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

export async function listDataSources(workspaceId) {
  const response = await api.get(API_ENDPOINTS.data.sources, {
    params: workspaceId ? { workspace: workspaceId } : undefined,
  });
  return response.data;
}

export async function getDataSource(sourceId) {
  const response = await api.get(API_ENDPOINTS.data.sourceDetail(sourceId));
  return response.data;
}

export async function createDataSource(payload) {
  const response = await api.post(API_ENDPOINTS.data.sources, payload);
  return response.data;
}

export async function updateDataSource(sourceId, payload) {
  const response = await api.patch(API_ENDPOINTS.data.sourceDetail(sourceId), payload);
  return response.data;
}

export async function deleteDataSource(sourceId) {
  await api.delete(API_ENDPOINTS.data.sourceDetail(sourceId));
}

export async function listDataAssets(workspaceId, assetType = "") {
  const params = {};
  if (workspaceId) params.workspace = workspaceId;
  if (assetType) params.asset_type = assetType;
  const response = await api.get(API_ENDPOINTS.data.assets, { params });
  return response.data;
}

export async function getDataAsset(assetId) {
  const response = await api.get(API_ENDPOINTS.data.assetDetail(assetId));
  return response.data;
}

export async function createDataAsset(payload) {
  const response = await api.post(API_ENDPOINTS.data.assets, payload);
  return response.data;
}

export async function updateDataAsset(assetId, payload) {
  const response = await api.patch(API_ENDPOINTS.data.assetDetail(assetId), payload);
  return response.data;
}

export async function deleteDataAsset(assetId) {
  await api.delete(API_ENDPOINTS.data.assetDetail(assetId));
}

export async function testDataSourceConnection(sourceId, runtimeCredentials = {}) {
  const response = await api.post(
    API_ENDPOINTS.connectors.test(sourceId),
    runtimeCredentials,
  );
  return response.data;
}

export async function previewDataSourceCatalog(sourceId, payload = {}) {
  const response = await api.post(API_ENDPOINTS.connectors.catalog(sourceId), payload);
  return response.data;
}

export async function readDataSourcePage(sourceId, payload) {
  const response = await api.post(API_ENDPOINTS.connectors.read(sourceId), payload);
  return response.data;
}


export async function listSourceBindings(workspaceId, sourceId) { const response=await api.get(API_ENDPOINTS.data.sourceBindings,{params:{workspace:workspaceId,source:sourceId}}); return response.data; }
export async function createSourceBinding(payload) { return (await api.post(API_ENDPOINTS.data.sourceBindings,payload)).data; }
export async function listPublishPlans(workspaceId, sourceId) { return (await api.get(API_ENDPOINTS.data.publishPlans,{params:{workspace:workspaceId,source:sourceId}})).data; }
export async function createPublishPlan(payload) { return (await api.post(API_ENDPOINTS.data.publishPlans,payload)).data; }
export async function updatePublishPlan(id,payload) { return (await api.patch(`${API_ENDPOINTS.data.publishPlans}${id}/`,payload)).data; }
export async function listWritebackPolicies(workspaceId, sourceId) { return (await api.get(API_ENDPOINTS.data.writebackPolicies,{params:{workspace:workspaceId,source:sourceId}})).data; }
export async function createWritebackPolicy(payload) { return (await api.post(API_ENDPOINTS.data.writebackPolicies,payload)).data; }
export async function deleteWritebackPolicy(id) { await api.delete(`${API_ENDPOINTS.data.writebackPolicies}${id}/`); }
