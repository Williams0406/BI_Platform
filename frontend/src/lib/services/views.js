import api from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

function unwrap(response) {
  return response.data;
}

export async function listViews({ workspace, viewType } = {}) {
  const params = {};
  if (workspace) params.workspace = workspace;
  if (viewType) params.view_type = viewType;
  return unwrap(await api.get(API_ENDPOINTS.views.list, { params }));
}

export async function getView(viewId) {
  return unwrap(await api.get(API_ENDPOINTS.views.detail(viewId)));
}

export async function createView(payload) {
  return unwrap(await api.post(API_ENDPOINTS.views.list, payload));
}

export async function updateView(viewId, payload) {
  return unwrap(await api.patch(API_ENDPOINTS.views.detail(viewId), payload));
}

export async function deleteView(viewId) {
  await api.delete(API_ENDPOINTS.views.detail(viewId));
}

export async function getViewSchema(viewId) {
  return unwrap(await api.get(API_ENDPOINTS.views.schema(viewId)));
}

export async function validateView(viewId) {
  return unwrap(await api.get(API_ENDPOINTS.views.validate(viewId)));
}

export async function getViewData(viewId, { limit = 100, offset = 0, orderBy = "", filters = [] } = {}) {
  const params = { limit, offset };
  if (orderBy) params.order_by = orderBy;
  filters.forEach((filter) => {
    if (!filter?.field || filter.value === "" || filter.value === undefined || filter.value === null) return;
    const operator = filter.operator && filter.operator !== "eq" ? `__${filter.operator}` : "";
    params[`filter__${filter.field}${operator}`] = filter.value;
  });
  return unwrap(await api.get(API_ENDPOINTS.views.data(viewId), { params }));
}

export async function createBinding(viewId, payload) {
  return unwrap(await api.post(API_ENDPOINTS.views.bindings(viewId), payload));
}

export async function deleteBinding(viewId, bindingId) {
  await api.delete(API_ENDPOINTS.views.bindingDetail(viewId, bindingId));
}

export async function createActionRule(viewId, payload) {
  return unwrap(await api.post(API_ENDPOINTS.views.actions(viewId), payload));
}

export async function interactWithView(viewId, { action, recordKey, expectedVersion, values }) {
  return unwrap(
    await api.post(API_ENDPOINTS.views.interact(viewId), {
      action,
      record_key: String(recordKey),
      expected_version: Number(expectedVersion),
      values,
    }),
  );
}

export async function saveViewBuilder(viewId, payload) {
  return unwrap(await api.put(API_ENDPOINTS.views.builder(viewId), payload));
}

export async function getOperationalQueryPlan(viewId) {
  return unwrap(await api.get(API_ENDPOINTS.views.operationalQuery(viewId)));
}

export async function executeOperationalQuery(viewId, payload = {}) {
  return unwrap(await api.post(API_ENDPOINTS.views.operationalQuery(viewId), payload));
}

export async function operationalWriteback(viewId, payload) {
  return unwrap(await api.post(API_ENDPOINTS.views.operationalWriteback(viewId), payload));
}
