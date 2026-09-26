import api from "@/lib/api/client";
import {notifyCodeDeletion} from "@/lib/storage/codeDeletion";
import {API_ENDPOINTS} from "@/lib/api/endpoints";
export async function listScriptBlocks(workspace){return (await api.get(API_ENDPOINTS.scripts.list,{params:{workspace}})).data}
export async function createScriptBlock(payload){return (await api.post(API_ENDPOINTS.scripts.list,payload)).data}
export async function updateScriptBlock(id,payload){return (await api.patch(API_ENDPOINTS.scripts.detail(id),payload)).data}
export async function deleteScriptBlock(id){return notifyCodeDeletion((await api.delete(API_ENDPOINTS.scripts.detail(id))).data)}
export async function analyzeScript(language,code){return (await api.post(API_ENDPOINTS.scripts.analyze,{language,code})).data}
export async function promoteScriptVariable(scriptId,artifactId){return (await api.post(`${API_ENDPOINTS.scripts.detail(scriptId)}promote-metric/`,{artifact_id:artifactId})).data}

export async function publishScriptBlock(id){return (await api.post(`${API_ENDPOINTS.scripts.detail(id)}publish/`,{})).data}

export async function executeScriptBlock(id,environmentId=null){return (await api.post(`${API_ENDPOINTS.scripts.detail(id)}execute/`,environmentId?{environment_id:environmentId}:{})).data}
export async function publishPythonVariable(id,variable,name=null,environmentId=null){return (await api.post(`${API_ENDPOINTS.scripts.detail(id)}publish-python-variable/`,{variable,name:name||variable,environment_id:environmentId||undefined})).data}

export async function registerPythonMLModel(id,variable,name=null,environmentId=null){return (await api.post(`${API_ENDPOINTS.scripts.detail(id)}register-ml-model/`,{variable,name:name||variable,environment_id:environmentId||undefined})).data}
