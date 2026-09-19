import api from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

function workspaceParams(workspaceId) {
  return workspaceId ? { workspace: workspaceId } : undefined;
}

export async function listCharts(workspaceId) {
  const response = await api.get(API_ENDPOINTS.analytics.charts, { params: workspaceParams(workspaceId) });
  return response.data;
}
export async function getChart(id) {
  const response = await api.get(API_ENDPOINTS.analytics.chartDetail(id));
  return response.data;
}
export async function createChart(payload) {
  const response = await api.post(API_ENDPOINTS.analytics.charts, payload);
  return response.data;
}
export async function updateChart(id, payload) {
  const response = await api.patch(API_ENDPOINTS.analytics.chartDetail(id), payload);
  return response.data;
}
export async function deleteChart(id) {
  await api.delete(API_ENDPOINTS.analytics.chartDetail(id));
}
export async function getChartDataset(id, payload = {}) {
  const response = await api.post(API_ENDPOINTS.analytics.chartDataset(id), payload);
  return response.data;
}
export async function getChartDrilldown(id, payload = {}) {
  const response = await api.post(API_ENDPOINTS.analytics.chartDrilldown(id), payload);
  return response.data;
}

export async function listDashboards(workspaceId) {
  const response = await api.get(API_ENDPOINTS.analytics.dashboards, { params: workspaceParams(workspaceId) });
  return response.data;
}
export async function getDashboard(id) {
  const response = await api.get(API_ENDPOINTS.analytics.dashboardDetail(id));
  return response.data;
}
export async function createDashboard(payload) {
  const response = await api.post(API_ENDPOINTS.analytics.dashboards, payload);
  return response.data;
}
export async function updateDashboard(id, payload) {
  const response = await api.patch(API_ENDPOINTS.analytics.dashboardDetail(id), payload);
  return response.data;
}
export async function deleteDashboard(id) {
  await api.delete(API_ENDPOINTS.analytics.dashboardDetail(id));
}
export async function getDashboardDataset(id, payload = {}) {
  const response = await api.post(API_ENDPOINTS.analytics.dashboardDataset(id), payload);
  return response.data;
}

export async function listDashboardItems(dashboardId) {
  const response = await api.get(API_ENDPOINTS.analytics.dashboardItems, {
    params: dashboardId ? { dashboard: dashboardId } : undefined,
  });
  return response.data;
}
export async function createDashboardItem(payload) {
  const response = await api.post(API_ENDPOINTS.analytics.dashboardItems, payload);
  return response.data;
}
export async function updateDashboardItem(id, payload) {
  const response = await api.patch(API_ENDPOINTS.analytics.dashboardItemDetail(id), payload);
  return response.data;
}
export async function deleteDashboardItem(id) {
  await api.delete(API_ENDPOINTS.analytics.dashboardItemDetail(id));
}

export async function listReports(workspaceId) {
  const response = await api.get(API_ENDPOINTS.analytics.reports, { params: workspaceParams(workspaceId) });
  return response.data;
}
export async function getReport(id) {
  const response = await api.get(API_ENDPOINTS.analytics.reportDetail(id));
  return response.data;
}
export async function createReport(payload) {
  const response = await api.post(API_ENDPOINTS.analytics.reports, payload);
  return response.data;
}
export async function updateReport(id, payload) {
  const response = await api.patch(API_ENDPOINTS.analytics.reportDetail(id), payload);
  return response.data;
}
export async function deleteReport(id) {
  await api.delete(API_ENDPOINTS.analytics.reportDetail(id));
}
