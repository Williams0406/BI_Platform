import api from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

function workspaceParams(workspaceId) {
  return workspaceId ? { workspace: workspaceId } : undefined;
}

export async function listPythonTransformations(workspaceId) {
  const response = await api.get(API_ENDPOINTS.dataScience.pythonTransformations, {
    params: workspaceParams(workspaceId),
  });
  return response.data;
}

export async function getPythonTransformation(id) {
  const response = await api.get(API_ENDPOINTS.dataScience.pythonTransformationDetail(id));
  return response.data;
}

export async function createPythonTransformation(payload) {
  const response = await api.post(API_ENDPOINTS.dataScience.pythonTransformations, payload);
  return response.data;
}

export async function updatePythonTransformation(id, payload) {
  const response = await api.patch(API_ENDPOINTS.dataScience.pythonTransformationDetail(id), payload);
  return response.data;
}

export async function deletePythonTransformation(id) {
  await api.delete(API_ENDPOINTS.dataScience.pythonTransformationDetail(id));
}

export async function addPythonTransformationInput(id, payload) {
  const response = await api.post(API_ENDPOINTS.dataScience.pythonTransformationInputs(id), payload);
  return response.data;
}

export async function runPythonTransformation(id) {
  const response = await api.post(API_ENDPOINTS.dataScience.pythonTransformationRun(id));
  return response.data;
}

export async function listDatasets(workspaceId) {
  const response = await api.get(API_ENDPOINTS.dataScience.datasets, {
    params: workspaceParams(workspaceId),
  });
  return response.data;
}

export async function createDataset(payload) {
  const response = await api.post(API_ENDPOINTS.dataScience.datasets, payload);
  return response.data;
}

export async function updateDataset(id, payload) {
  const response = await api.patch(API_ENDPOINTS.dataScience.datasetDetail(id), payload);
  return response.data;
}

export async function deleteDataset(id) {
  await api.delete(API_ENDPOINTS.dataScience.datasetDetail(id));
}

export async function listModels(workspaceId) {
  const response = await api.get(API_ENDPOINTS.dataScience.models, {
    params: workspaceParams(workspaceId),
  });
  return response.data;
}

export async function getModel(id) {
  const response = await api.get(API_ENDPOINTS.dataScience.modelDetail(id));
  return response.data;
}

export async function createModel(payload) {
  const response = await api.post(API_ENDPOINTS.dataScience.models, payload);
  return response.data;
}

export async function updateModel(id, payload) {
  const response = await api.patch(API_ENDPOINTS.dataScience.modelDetail(id), payload);
  return response.data;
}

export async function deleteModel(id) {
  await api.delete(API_ENDPOINTS.dataScience.modelDetail(id));
}

export async function trainModel(id) {
  const response = await api.post(API_ENDPOINTS.dataScience.modelTrain(id));
  return response.data;
}

export async function listModelRuns(modelId) {
  const response = await api.get(API_ENDPOINTS.dataScience.runs, {
    params: modelId ? { model: modelId } : undefined,
  });
  return response.data;
}

export async function getModelRun(id) {
  const response = await api.get(API_ENDPOINTS.dataScience.runDetail(id));
  return response.data;
}

export async function listModelVersions(modelId) {
  const response = await api.get(API_ENDPOINTS.dataScience.versions, {
    params: modelId ? { model: modelId } : undefined,
  });
  return response.data;
}

export async function getModelVersion(id) {
  const response = await api.get(API_ENDPOINTS.dataScience.versionDetail(id));
  return response.data;
}

export async function inferModelVersion(id, datasetId) {
  const response = await api.post(API_ENDPOINTS.dataScience.versionInfer(id), {
    dataset: datasetId,
  });
  return response.data;
}

export async function listPredictions() {
  const response = await api.get(API_ENDPOINTS.dataScience.predictions);
  return response.data;
}
