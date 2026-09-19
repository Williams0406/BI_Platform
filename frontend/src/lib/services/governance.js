import api from "@/lib/api/client";
import {API_ENDPOINTS} from "@/lib/api/endpoints";
const data=r=>r.data;
export async function listAudit(workspace){return data(await api.get(API_ENDPOINTS.governance.audit,{params:{workspace}}));}
export async function listPermissions(){return data(await api.get(API_ENDPOINTS.governance.permissions));}
export async function createPermission(payload){return data(await api.post(API_ENDPOINTS.governance.permissions,payload));}
export async function updatePermission(id,payload){return data(await api.patch(API_ENDPOINTS.governance.permissionDetail(id),payload));}
export async function deletePermission(id){return api.delete(API_ENDPOINTS.governance.permissionDetail(id));}
export async function getQuota(id){return data(await api.get(API_ENDPOINTS.governance.quota(id)));}
export async function updateQuota(id,payload){return data(await api.patch(API_ENDPOINTS.governance.quota(id),payload));}
export async function getUsage(id){return data(await api.get(API_ENDPOINTS.governance.usage(id)));}
export async function getPolicy(id){return data(await api.get(API_ENDPOINTS.governance.policy(id)));}
export async function updatePolicy(id,payload){return data(await api.patch(API_ENDPOINTS.governance.policy(id),payload));}
export async function listCredentialStatus(workspace){return data(await api.get(API_ENDPOINTS.governance.secrets,{params:{workspace}}));}
export async function getRetention(id){return data(await api.get(API_ENDPOINTS.governance.retention(id)));}
export async function updateRetention(id,payload){return data(await api.patch(API_ENDPOINTS.governance.retention(id),payload));}
export async function getSecretStatus(sourceId){return data(await api.get(API_ENDPOINTS.governance.secretDetail(sourceId)));}
export async function setDataSourceSecret(sourceId,credentials){return data(await api.post(API_ENDPOINTS.governance.secrets,{data_source:sourceId,credentials}));}
export async function listDestructiveRequests(){return data(await api.get(API_ENDPOINTS.governance.destructiveRequests));}
export async function createDestructiveRequest(payload){return data(await api.post(API_ENDPOINTS.governance.destructiveRequests,payload));}
export async function approveDestructiveRequest(id){return data(await api.post(API_ENDPOINTS.governance.destructiveApprove(id),{}));}

export async function listWorkspaceMembers(id){return data(await api.get(API_ENDPOINTS.governance.members(id)));}
export async function listCopyEvents(workspace,source){return data(await api.get(API_ENDPOINTS.governance.copyEvents,{params:{workspace,source}}));}
export async function createCopyEvent(payload){return data(await api.post(API_ENDPOINTS.governance.copyEvents,payload));}
