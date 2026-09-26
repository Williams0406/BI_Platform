import api from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

export async function listCatalogTables(dataSourceId, schema = "", workspaceId = "") {
  const params = {};
  if (dataSourceId) params.data_source = dataSourceId;
  if (schema) params.schema = schema;
  if (workspaceId) params.workspace = workspaceId;
  const response = await api.get(API_ENDPOINTS.catalog.tables, { params });
  return response.data;
}

export async function renameCatalogTable(tableId, technicalName) {
  const response = await api.patch(API_ENDPOINTS.catalog.tableDetail(tableId), { technical_name: technicalName });
  return response.data;
}

export async function deleteCatalogTable(tableId) {
  await api.delete(API_ENDPOINTS.catalog.tableDetail(tableId));
}

export async function getCatalogTable(tableId) {
  const response = await api.get(API_ENDPOINTS.catalog.tableDetail(tableId));
  return response.data;
}

export async function createCatalogRelation(payload) {
  const response = await api.post(API_ENDPOINTS.catalog.relations, payload);
  return response.data;
}

export async function deleteCatalogRelation(relationId) {
  await api.delete(`${API_ENDPOINTS.catalog.relations}${relationId}/`);
}

export async function listCatalogRelations(dataSourceId) {
  const params = dataSourceId ? { data_source: dataSourceId } : undefined;
  const response = await api.get(API_ENDPOINTS.catalog.relations, { params });
  return response.data;
}

export async function syncCatalog(dataSourceId, payload = {}) {
  const response = await api.post(API_ENDPOINTS.catalog.sync(dataSourceId), payload);
  return response.data;
}

export async function createManagedTable(payload) {
  const response = await api.post(API_ENDPOINTS.catalog.managedTables, payload);
  return response.data;
}

export async function deleteManagedTable(tableId) {
  await api.delete(API_ENDPOINTS.catalog.managedTableDetail(tableId));
}


export async function createPlatformField(payload) {
  const response = await api.post(API_ENDPOINTS.catalog.platformFields, payload);
  return response.data;
}

export async function listFieldContentRules(tableId) {
  const response = await api.get(API_ENDPOINTS.catalog.fieldContentRules, { params: tableId ? { table: tableId } : undefined });
  return response.data;
}

export async function saveFieldContentRule(payload, existingId = null) {
  const response = existingId
    ? await api.patch(API_ENDPOINTS.catalog.fieldContentRuleDetail(existingId), payload)
    : await api.post(API_ENDPOINTS.catalog.fieldContentRules, payload);
  return response.data;
}
