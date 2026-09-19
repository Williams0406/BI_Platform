import api from "@/lib/api/client";
import {API_ENDPOINTS} from "@/lib/api/endpoints";
const data=r=>r.data;
export async function listGateways(workspace){return data(await api.get(API_ENDPOINTS.gateway.registrations,{params:{workspace}}));}
export async function registerGateway(payload){return data(await api.post(API_ENDPOINTS.gateway.register,payload));}
export async function renewGateway(id){return data(await api.post(API_ENDPOINTS.gateway.renew(id),{}));}
export async function revokeGateway(id){return data(await api.post(API_ENDPOINTS.gateway.revoke(id),{}));}
export async function listBindings(){return data(await api.get(API_ENDPOINTS.gateway.bindings));}
export async function createBinding(payload){return data(await api.post(API_ENDPOINTS.gateway.bindings,payload));}
export async function updateBinding(id,payload){return data(await api.patch(API_ENDPOINTS.gateway.bindingDetail(id),payload));}
export async function deleteBinding(id){return api.delete(API_ENDPOINTS.gateway.bindingDetail(id));}
export async function listGatewayJobs(sourceId){return data(await api.get(API_ENDPOINTS.gateway.jobs,{params:sourceId?{data_source:sourceId}:{}}));}
export async function queueGatewayJob(sourceId,payload){return data(await api.post(API_ENDPOINTS.gateway.queue(sourceId),payload));}
export async function listGatewayImports(workspace){return data(await api.get(API_ENDPOINTS.gateway.imports,{params:{workspace}}));}
export async function createGatewayImport(payload){return data(await api.post(API_ENDPOINTS.gateway.imports,payload));}
