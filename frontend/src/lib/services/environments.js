import api from "@/lib/api/client"; import {API_ENDPOINTS} from "@/lib/api/endpoints";
export async function listComputeTargets(workspace){return (await api.get(API_ENDPOINTS.environments.targets,{params:{workspace}})).data}
export async function createComputeTarget(payload){return (await api.post(API_ENDPOINTS.environments.targets,payload)).data}
export async function listEnvironments(workspace){return (await api.get(API_ENDPOINTS.environments.list,{params:{workspace}})).data}
export async function createEnvironment(payload){return (await api.post(API_ENDPOINTS.environments.list,payload)).data}
export async function addEnvironmentPackage(payload){return (await api.post(API_ENDPOINTS.environments.packages,payload)).data}
export async function deleteEnvironmentPackage(id){return api.delete(`${API_ENDPOINTS.environments.packages}${id}/`)}
