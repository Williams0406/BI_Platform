import { listCharts, listDashboards, listReports } from "@/lib/services/analytics";
import { listDataAssets, listDataSources } from "@/lib/services/dataSources";
import { listModels, listPythonTransformations } from "@/lib/services/dataScience";
import { listDependencies } from "@/lib/services/dependencies";
import { listExecutions } from "@/lib/services/executions";
import { listExports, listImports } from "@/lib/services/importExport";
import { listMetrics, listSemanticModels } from "@/lib/services/metrics";
import { listOptimizationModels } from "@/lib/services/optimization";
import { listTransformations } from "@/lib/services/transformations";
import { listViews } from "@/lib/services/views";
import { listGateways } from "@/lib/services/customerGateway";

function collectionSize(value) {
  if (Array.isArray(value)) return value.length;
  if (Array.isArray(value?.results)) return value.results.length;
  if (typeof value?.count === "number") return value.count;
  return 0;
}

function failureMessage(reason) {
  if (reason?.response?.status) return `HTTP ${reason.response.status}`;
  if (reason?.code === "ECONNABORTED") return "timeout";
  return reason?.message || "error";
}

export async function validateWorkspaceIntegration(workspaceId) {
  if (!workspaceId) return [];

  const checks = [
    ["Data Sources", "/app/data-sources", () => listDataSources(workspaceId)],
    ["Data Assets", "/app/data-assets", () => listDataAssets(workspaceId)],
    ["Operational Views", "/app/views", () => listViews({ workspace: workspaceId })],
    ["SQL Transformations", "/app/transformations", () => listTransformations(workspaceId)],
    ["Dependencies", "/app/dependencies", () => listDependencies(workspaceId)],
    ["Executions", "/app/executions", () => listExecutions({ workspace: workspaceId })],
    ["Semantic Models", "/app/metrics", () => listSemanticModels(workspaceId)],
    ["Metrics", "/app/metrics", () => listMetrics(workspaceId)],
    ["Charts", "/app/analytics", () => listCharts(workspaceId)],
    ["Dashboards", "/app/dashboards", () => listDashboards(workspaceId)],
    ["Reports", "/app/reports", () => listReports(workspaceId)],
    ["Python Transformations", "/app/data-science", () => listPythonTransformations(workspaceId)],
    ["ML Models", "/app/data-science", () => listModels(workspaceId)],
    ["Optimization Models", "/app/optimization", () => listOptimizationModels(workspaceId)],
    ["Imports", "/app/import-export", () => listImports(workspaceId)],
    ["Exports", "/app/import-export", () => listExports(workspaceId)],
    ["Customer Gateways", "/app/customer-gateway", () => listGateways(workspaceId)],
  ];

  const settled = await Promise.allSettled(checks.map(([, , load]) => load()));

  return settled.map((result, index) => {
    const [name, href] = checks[index];
    if (result.status === "fulfilled") {
      return {
        name,
        href,
        ok: true,
        count: collectionSize(result.value),
        detail: "Endpoint accesible",
      };
    }
    return {
      name,
      href,
      ok: false,
      count: null,
      detail: failureMessage(result.reason),
    };
  });
}
