import api from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

const data = (response) => response.data;

export async function listImports(workspace) {
  return data(await api.get(API_ENDPOINTS.importExport.imports, { params: { workspace } }));
}

export async function inspectImportFile(formData) {
  return data(await api.post(`${API_ENDPOINTS.importExport.imports}inspect/`, formData, { headers: { "Content-Type": "multipart/form-data" } }));
}

export async function createImport(formData) {
  return data(await api.post(API_ENDPOINTS.importExport.imports, formData, { headers: { "Content-Type": "multipart/form-data" } }));
}

export async function previewImport(id) {
  return data(await api.get(API_ENDPOINTS.importExport.importPreview(id)));
}

export async function runImport(id) {
  return data(await api.post(API_ENDPOINTS.importExport.importRun(id), {}));
}

export async function listSyncPolicies(workspace, sourceDataSource = "") {
  const params = {};
  if (workspace) params.workspace = workspace;
  if (sourceDataSource) params.source_data_source = sourceDataSource;
  return data(await api.get(API_ENDPOINTS.importExport.syncPolicies, { params }));
}

export async function createSyncPolicy(payload) {
  return data(await api.post(API_ENDPOINTS.importExport.syncPolicies, payload));
}

export async function updateSyncPolicy(id, payload) {
  return data(await api.patch(API_ENDPOINTS.importExport.syncPolicyDetail(id), payload));
}

export async function deleteSyncPolicy(id) {
  await api.delete(API_ENDPOINTS.importExport.syncPolicyDetail(id));
}

export async function runSyncPolicy(id) {
  return data(await api.post(API_ENDPOINTS.importExport.syncPolicyRun(id), {}));
}

export async function listExports(workspace) {
  return data(await api.get(API_ENDPOINTS.importExport.exports, { params: { workspace } }));
}

export async function getExport(id) {
  return data(await api.get(`${API_ENDPOINTS.importExport.exports}${id}/`));
}

export async function createExport(payload) {
  return data(await api.post(API_ENDPOINTS.importExport.exports, payload));
}

export async function downloadExport(id) {
  return (await api.get(API_ENDPOINTS.importExport.exportDownload(id), { responseType: "blob" })).data;
}
