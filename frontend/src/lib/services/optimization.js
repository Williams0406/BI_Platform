import api from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

const params = (values) => Object.fromEntries(Object.entries(values || {}).filter(([,v]) => v !== undefined && v !== null && v !== ""));

export async function listOptimizationModels(workspace){ const r=await api.get(API_ENDPOINTS.optimization.models,{params:params({workspace})}); return r.data; }
export async function getOptimizationModel(id){ const r=await api.get(API_ENDPOINTS.optimization.modelDetail(id)); return r.data; }
export async function createOptimizationModel(payload){ const r=await api.post(API_ENDPOINTS.optimization.models,payload); return r.data; }
export async function updateOptimizationModel(id,payload){ const r=await api.patch(API_ENDPOINTS.optimization.modelDetail(id),payload); return r.data; }
export async function deleteOptimizationModel(id){ await api.delete(API_ENDPOINTS.optimization.modelDetail(id)); }
export async function validateOptimizationModel(id){ const r=await api.get(API_ENDPOINTS.optimization.modelValidate(id)); return r.data; }
export async function runOptimizationModel(id,payload){ const r=await api.post(API_ENDPOINTS.optimization.modelRun(id),payload); return r.data; }

function crud(base, detail){ return {
 list: async (filter={}) => (await api.get(base,{params:params(filter)})).data,
 create: async payload => (await api.post(base,payload)).data,
 update: async (id,payload) => (await api.patch(detail(id),payload)).data,
 remove: async id => { await api.delete(detail(id)); },
}; }
export const optimizationParameters=crud(API_ENDPOINTS.optimization.parameters,API_ENDPOINTS.optimization.parameterDetail);
export const optimizationVariables=crud(API_ENDPOINTS.optimization.variables,API_ENDPOINTS.optimization.variableDetail);
export const optimizationObjectives=crud(API_ENDPOINTS.optimization.objectives,API_ENDPOINTS.optimization.objectiveDetail);
export const optimizationConstraints=crud(API_ENDPOINTS.optimization.constraints,API_ENDPOINTS.optimization.constraintDetail);
export const solverConfigs=crud(API_ENDPOINTS.optimization.solverConfigs,API_ENDPOINTS.optimization.solverConfigDetail);
export const optimizationScenarios=crud(API_ENDPOINTS.optimization.scenarios,API_ENDPOINTS.optimization.scenarioDetail);
export async function listOptimizationRuns(filter={}){ const r=await api.get(API_ENDPOINTS.optimization.runs,{params:params(filter)}); return r.data; }
export async function getOptimizationRun(id){ const r=await api.get(API_ENDPOINTS.optimization.runDetail(id)); return r.data; }
export async function listOptimizationSolutions(filter={}){ const r=await api.get(API_ENDPOINTS.optimization.solutions,{params:params(filter)}); return r.data; }
