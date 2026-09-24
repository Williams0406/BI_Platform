import api from "@/lib/api/client";
import {API_ENDPOINTS} from "@/lib/api/endpoints";
export async function listScriptBlocks(workspace){return (await api.get(API_ENDPOINTS.scripts.list,{params:{workspace}})).data}
export async function createScriptBlock(payload){return (await api.post(API_ENDPOINTS.scripts.list,payload)).data}
export async function updateScriptBlock(id,payload){return (await api.patch(API_ENDPOINTS.scripts.detail(id),payload)).data}
export async function deleteScriptBlock(id){await api.delete(API_ENDPOINTS.scripts.detail(id));return {deleted:true}}
export async function analyzeScript(language,code){return (await api.post(API_ENDPOINTS.scripts.analyze,{language,code})).data}
export async function promoteScriptVariable(scriptId,artifactId){return (await api.post(`${API_ENDPOINTS.scripts.detail(scriptId)}promote-metric/`,{artifact_id:artifactId})).data}
