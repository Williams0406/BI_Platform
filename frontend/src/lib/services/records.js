import api from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

export async function listRecords(tableId, options = {}) {
  const params = {};
  if (options.limit) params.limit = options.limit;
  if (Number.isFinite(options.offset)) params.offset = options.offset;
  if (options.orderBy) params.order_by = options.orderBy;

  for (const filter of options.filters || []) {
    if (!filter.field || filter.value === "") continue;
    const operator = filter.operator || "eq";
    const suffix = operator === "eq" ? "" : `__${operator}`;
    params[`filter__${filter.field}${suffix}`] = filter.value;
  }

  const response = await api.get(API_ENDPOINTS.records.collection(tableId), { params });
  return response.data;
}

export async function getRecord(tableId, recordKey) {
  const response = await api.get(API_ENDPOINTS.records.detail(tableId, recordKey));
  return response.data;
}

export async function createRecord(tableId, payload) {
  const response = await api.post(API_ENDPOINTS.records.collection(tableId), payload);
  return response.data;
}

export async function updateRecord(tableId, recordKey, payload, expectedVersion) {
  const response = await api.patch(
    API_ENDPOINTS.records.detail(tableId, recordKey),
    payload,
    { headers: { "If-Match-Version": String(expectedVersion) } },
  );
  return response.data;
}

export async function deleteRecord(tableId, recordKey, expectedVersion) {
  const response = await api.delete(
    API_ENDPOINTS.records.detail(tableId, recordKey),
    { headers: { "If-Match-Version": String(expectedVersion) } },
  );
  return response.data;
}
