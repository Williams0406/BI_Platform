import { listCharts, listDashboards, listReports } from "@/lib/services/analytics";
import { listDataAssets, listDataSources } from "@/lib/services/dataSources";
import { listModels } from "@/lib/services/dataScience";
import { listOptimizationModels } from "@/lib/services/optimization";
import { listViews } from "@/lib/services/views";

function rows(value) {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.results)) return value.results;
  return [];
}

function item(type, icon, href, raw, subtitle = "") {
  return { id: `${type}:${raw.id}`, resourceId: raw.id, type, icon, title: raw.name || raw.email || String(raw.id), subtitle, href, raw };
}

export async function searchWorkspace(workspaceId, query = "") {
  if (!workspaceId) return [];
  const loaders = [
    ["Data source", "plug", listDataSources(workspaceId), (x) => `/app/data-sources/${x.id}`, (x) => `${x.mode || ""} ${x.engine || ""}`],
    ["Data asset", "catalog", listDataAssets(workspaceId), (x) => `/app/data-assets/${x.id}`, (x) => x.asset_type || ""],
    ["Operational view", "view", listViews({ workspace: workspaceId }), (x) => `/app/views/${x.id}`, (x) => x.view_type || ""],
    ["Chart", "explore", listCharts(workspaceId), (x) => `/app/analytics/${x.id}`, (x) => x.chart_type || ""],
    ["Dashboard", "dashboard", listDashboards(workspaceId), (x) => `/app/dashboards/${x.id}`, () => "Dashboard"],
    ["Report", "report", listReports(workspaceId), (x) => `/app/reports/${x.id}`, () => "Report"],
    ["ML model", "brain", listModels(workspaceId), (x) => `/app/data-science/models/${x.id}`, (x) => x.algorithm || ""],
    ["Optimization", "optimize", listOptimizationModels(workspaceId), (x) => `/app/optimization/${x.id}`, (x) => x.problem_type || ""],
  ];
  const settled = await Promise.allSettled(loaders.map((entry) => entry[2]));
  const all = [];
  settled.forEach((result, index) => {
    if (result.status !== "fulfilled") return;
    const [type, icon, , href, subtitle] = loaders[index];
    rows(result.value).forEach((raw) => all.push(item(type, icon, href(raw), raw, subtitle(raw))));
  });
  const needle = query.trim().toLowerCase();
  const filtered = needle ? all.filter((x) => `${x.title} ${x.subtitle} ${x.type}`.toLowerCase().includes(needle)) : all;
  return filtered.sort((a, b) => a.title.localeCompare(b.title)).slice(0, 40);
}
