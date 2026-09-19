import api from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

export async function listOrganizations() {
  const response = await api.get(API_ENDPOINTS.workspaces.organizations);
  return response.data;
}

export async function getOrganization(organizationId) {
  const response = await api.get(
    API_ENDPOINTS.workspaces.organizationDetail(organizationId),
  );
  return response.data;
}

export async function createOrganization(payload) {
  const response = await api.post(API_ENDPOINTS.workspaces.organizations, payload);
  return response.data;
}

export async function updateOrganization(organizationId, payload) {
  const response = await api.patch(
    API_ENDPOINTS.workspaces.organizationDetail(organizationId),
    payload,
  );
  return response.data;
}

export async function deleteOrganization(organizationId) {
  await api.delete(API_ENDPOINTS.workspaces.organizationDetail(organizationId));
}

export async function listWorkspaces() {
  const response = await api.get(API_ENDPOINTS.workspaces.list);
  return response.data;
}

export async function getWorkspace(workspaceId) {
  const response = await api.get(API_ENDPOINTS.workspaces.detail(workspaceId));
  return response.data;
}

export async function createWorkspace(payload) {
  const response = await api.post(API_ENDPOINTS.workspaces.list, payload);
  return response.data;
}

export async function updateWorkspace(workspaceId, payload) {
  const response = await api.patch(
    API_ENDPOINTS.workspaces.detail(workspaceId),
    payload,
  );
  return response.data;
}

export async function deleteWorkspace(workspaceId) {
  await api.delete(API_ENDPOINTS.workspaces.detail(workspaceId));
}
