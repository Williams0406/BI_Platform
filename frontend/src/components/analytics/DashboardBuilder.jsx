"use client";
import SharedDataPanel from "@/components/data/SharedDataPanel";
import ScriptWorkbench from "@/components/data/ScriptWorkbench";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { normalizeAnalyticsFilters } from "@/components/analytics/AnalyticsFilterBuilder";
import ChartRenderer from "@/components/analytics/ChartRenderer";
import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import {
  createChart,
  createDashboardItem,
  deleteDashboardItem,
  getDashboard,
  getDashboardDataset,
  listCharts,
  updateChart,
  updateDashboard,
  updateDashboardItem,
} from "@/lib/services/analytics";
import { getCatalogTable, listCatalogTables } from "@/lib/services/dataModel";
import { listDataSources } from "@/lib/services/dataSources";
import {
  createDimension,
  createMetric,
  createSemanticModel,
  listMetrics,
  listSemanticModels,
} from "@/lib/services/metrics";
import { getApiErrorMessage } from "@/lib/utils/errors";
import {createScriptBlock} from "@/lib/services/scripts";
import { getAccessToken } from "@/lib/auth/tokens";

const COLS = 12;
const ROW = 86;
const GAP = 12;
const VISUAL_TYPES = ["KPI", "BAR", "LINE", "AREA", "PIE", "DONUT", "SCATTER", "TABLE", "SLICER"];
const DEFAULT_STYLE = {
  backgroundColor: "#ffffff",
  accentColor: "#4d6072",
  textColor: "#1f2937",
  titleColor: "#1f2937",
  borderColor: "#dfe3e8",
  borderRadius: 8,
  fontFamily: "Inter, system-ui, sans-serif",
  fontSize: 12,
  titleFontSize: 13,
  titleFontWeight: 650,
  showTitle: true,
  showLegend: true,
  showDataLabels: false,
  showGridlines: true,
};

function listValue(data) {
  return Array.isArray(data) ? data : data?.results || [];
}
function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}
function pos(value, index = 0) {
  const p = value || {};
  const y = Number(p.y);
  return {
    x: clamp(Number(p.x) || 0, 0, 11),
    y: Number.isFinite(y) ? Math.max(0, y) : Math.floor(index / 2) * 4,
    w: clamp(Number(p.w) || 6, 2, 12),
    h: clamp(Number(p.h) || 4, 2, 12),
  };
}
function nextPosition(items) {
  if (!items.length) return { x: 0, y: 0, w: 6, h: 4 };
  const bottom = Math.max(
    ...items.map((item, index) => {
      const p = pos(item.position, index);
      return p.y + p.h;
    })
  );
  return { x: 0, y: bottom, w: 6, h: 4 };
}
function intersectFields(tables) {
  if (!tables.length) return [];
  const maps = tables.map((table) => new Map((table.fields || []).map((field) => [field.name, field])));
  return [...maps[0].values()].filter((field) => maps.every((map) => map.has(field.name)));
}
function pageId() {
  return `page-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}
function normalizePages(layout) {
  const pages = Array.isArray(layout?.pages) ? layout.pages.filter((page) => page?.id && page?.name) : [];
  return pages.length ? pages : [{ id: "page-1", name: "Page 1" }];
}
function itemPage(item, firstPageId) {
  return item?.config_override?.page_id || firstPageId;
}
function itemStyle(item) {
  return { ...DEFAULT_STYLE, ...(item?.config_override?.style || {}) };
}
function chartTypeLabel(type) {
  const labels = { KPI: "Card", BAR: "Column", LINE: "Line", AREA: "Area", PIE: "Pie", DONUT: "Donut", SCATTER: "Scatter", TABLE: "Table", SLICER: "Slicer" };
  return labels[type] || type;
}
function VisualGlyph({ type }) {
  if (type === "KPI") return <span className="visualGlyphKpi">123</span>;
  if (type === "TABLE") return <span className="visualGlyphTable">▦</span>;
  if (type === "PIE" || type === "DONUT") return <span className="visualGlyphPie">◕</span>;
  if (type === "LINE" || type === "AREA") return <span className="visualGlyphLine">⌁</span>;
  if (type === "SCATTER") return <span className="visualGlyphScatter">⠿</span>;
  if (type === "SLICER") return <span className="visualGlyphSlicer">▽</span>;
  return <span className="visualGlyphBar">▥</span>;
}

export default function DashboardBuilder({ dashboardId, workspaceId, canWrite, draftMode = false, onPublished }) {
  const [dashboard, setDashboard] = useState(null);
  const [charts, setCharts] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [models, setModels] = useState([]);
  const [tables, setTables] = useState([]);
  const [activeTableId, setActiveTableId] = useState("");
  const [measureLanguage, setMeasureLanguage] = useState("DAX");
  const [measureCode, setMeasureCode] = useState("");
  const [semanticBusy, setSemanticBusy] = useState(false);
  const [dataset, setDataset] = useState(null);
  const [commonFields, setCommonFields] = useState([]);
  const [runtimeFilters, setRuntimeFilters] = useState([]);
  const [useCache, setUseCache] = useState(true);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [editMode, setEditMode] = useState(Boolean(canWrite));
  const [selected, setSelected] = useState(null);
  const [saving, setSaving] = useState(false);
  const [nameDraft, setNameDraft] = useState("");
  const [rightOpen, setRightOpen] = useState(true);
  const [visualTab, setVisualTab] = useState("build");
  const [canvasZoom, setCanvasZoom] = useState(1);
  const [canvasZoomMode, setCanvasZoomMode] = useState("fit");
  const [activePageId, setActivePageId] = useState(null);
  const [renamingPage, setRenamingPage] = useState(null);
  const [pageDraft, setPageDraft] = useState("");
  const canvasRef = useRef(null);
  const viewportRef = useRef(null);
  const gesture = useRef(null);
  const publishedRef = useRef(false);

  const pages = useMemo(() => normalizePages(dashboard?.layout), [dashboard?.layout]);
  const effectivePageId = activePageId && pages.some((page) => page.id === activePageId) ? activePageId : pages[0]?.id;
  const pageItems = useMemo(
    () => (dashboard?.items || []).filter((item) => itemPage(item, pages[0]?.id) === effectivePageId),
    [dashboard?.items, pages, effectivePageId]
  );
  const dataByItem = useMemo(() => new Map((dataset?.items || []).map((item) => [String(item.item_id), item])), [dataset]);
  const chartMap = useMemo(() => new Map(charts.map((chart) => [String(chart.id), chart])), [charts]);
  const selectedItem = useMemo(
    () => dashboard?.items?.find((item) => String(item.id) === String(selected)) || null,
    [dashboard, selected]
  );
  const selectedChart = selectedItem ? chartMap.get(String(selectedItem.chart)) : null;
  const selectedMetric = selectedChart ? metrics.find((metric) => String(metric.id) === String(selectedChart.metric)) : null;
  const selectedModel = selectedMetric ? models.find((model) => String(model.id) === String(selectedMetric.semantic_model)) : null;
  const visibleMetrics = useMemo(() => metrics.filter((metric) => !String(metric.name || "").startsWith("__auto_visual__")), [metrics]);
  const modelMetrics = useMemo(
    () => visibleMetrics.filter((metric) => !selectedModel || String(metric.semantic_model) === String(selectedModel.id)),
    [visibleMetrics, selectedModel]
  );
  const autoBindings = dashboard?.layout?.auto_semantic_models || [];
  const dashboardModelIds = useMemo(() => new Set(autoBindings.map((binding) => String(binding.model_id))), [dashboard?.layout]);
  const dashboardMetrics = useMemo(() => visibleMetrics.filter((metric) => dashboardModelIds.has(String(metric.semantic_model))), [visibleMetrics, dashboardModelIds]);
  const activeTable = useMemo(() => tables.find((table) => String(table.id) === String(activeTableId)) || null, [tables, activeTableId]);

  function modelForTable(tableId) {
    const binding = autoBindings.find((item) => String(item.table_id) === String(tableId));
    return binding ? models.find((model) => String(model.id) === String(binding.model_id)) || null : null;
  }

  async function selectTable(tableId) {
    setActiveTableId(String(tableId || ""));
    if (tableId && canWrite && dashboard) {
      try { await ensureSemanticModel(tableId); } catch (e) { setError(getApiErrorMessage(e)); }
    }
  }

  async function load({ quiet = false } = {}) {
    if (!dashboardId || !workspaceId) return;
    if (!quiet) setLoading(true);
    setError("");
    try {
      const [d, c, m, s, sourceResponse] = await Promise.all([
        getDashboard(dashboardId),
        listCharts(workspaceId),
        listMetrics(workspaceId),
        listSemanticModels(workspaceId),
        listDataSources(workspaceId),
      ]);
      const chartList = listValue(c);
      const metricList = listValue(m);
      const modelList = listValue(s);
      setDashboard(d);
      setNameDraft(d.name || "Untitled dashboard");
      setCharts(chartList);
      setMetrics(metricList);
      setModels(modelList);
      const sourceList = listValue(sourceResponse);
      const tableResponses = await Promise.all(sourceList.map((source) => listCatalogTables(source.id).catch(() => [])));
      const tableList = tableResponses.flatMap(listValue);
      setTables(tableList);
      setActiveTableId((current) => current || String(tableList[0]?.id || ""));
      const modelIds = new Set(
        (d.items || [])
          .map((item) => metricList.find((metric) => String(metric.id) === String(chartList.find((chart) => String(chart.id) === String(item.chart))?.metric))?.semantic_model)
          .filter(Boolean)
      );
      const tables = await Promise.all(
        [...modelIds].map((modelId) => {
          const model = modelList.find((entry) => String(entry.id) === String(modelId));
          return model ? getCatalogTable(model.base_table) : null;
        })
      );
      setCommonFields(intersectFields(tables.filter(Boolean)));
      const normalized = normalizePages(d.layout);
      setActivePageId((current) => (current && normalized.some((page) => page.id === current) ? current : normalized[0].id));
    } catch (e) {
      setError(getApiErrorMessage(e));
    } finally {
      if (!quiet) setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [dashboardId, workspaceId]);

  useEffect(() => {
    if (!draftMode || !dashboardId) return undefined;
    const cleanupDraft = () => {
      if (publishedRef.current) return;
      const token = getAccessToken();
      const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api/v1";
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const bindings = dashboard?.layout?.auto_semantic_models || [];
      for (const binding of bindings) {
        if (!binding?.model_id) continue;
        try { fetch(`${base}/metrics/semantic-models/${binding.model_id}/`, { method: "DELETE", headers, keepalive: true }); } catch {}
      }
      try { fetch(`${base}/analytics/dashboards/${dashboardId}/`, { method: "DELETE", headers, keepalive: true }); } catch {}
    };
    window.addEventListener("pagehide", cleanupDraft);
    return () => window.removeEventListener("pagehide", cleanupDraft);
  }, [draftMode, dashboardId, dashboard?.layout]);

  useEffect(() => {
    if (canvasZoomMode !== "fit") return undefined;
    const viewport = viewportRef.current;
    if (!viewport) return undefined;
    const fit = () => {
      const width = Number(dashboard?.layout?.canvas?.width) || 1280;
      const available = Math.max(280, viewport.clientWidth - 44);
      setCanvasZoom(clamp(available / width, 0.25, 1));
    };
    fit();
    const observer = typeof ResizeObserver !== "undefined" ? new ResizeObserver(fit) : null;
    observer?.observe(viewport);
    window.addEventListener("resize", fit);
    return () => { observer?.disconnect(); window.removeEventListener("resize", fit); };
  }, [canvasZoomMode, dashboard?.layout?.canvas?.width, rightOpen, editMode]);

  useEffect(() => {
    if (dashboard?.items?.length) run();
    else setDataset(null);
  }, [dashboard?.id, dashboard?.items?.length]);

  async function run(filtersOverride = null) {
    if (!dashboardId || !dashboard?.items?.length) return;
    setRunning(true);
    setError("");
    try {
      const activeFilters = filtersOverride || runtimeFilters;
      setDataset(await getDashboardDataset(dashboardId, { filters: normalizeAnalyticsFilters(activeFilters), use_cache: useCache }));
    } catch (e) {
      setError(getApiErrorMessage(e));
    } finally {
      setRunning(false);
    }
  }

  async function ensureSemanticModel(tableId) {
    if (!tableId || !dashboard) return null;
    const existing = modelForTable(tableId);
    if (existing) return existing;
    const table = tables.find((item) => String(item.id) === String(tableId));
    if (!table) throw new Error("Select a table first.");
    setSemanticBusy(true);
    try {
      const created = await createSemanticModel({
        workspace: workspaceId,
        name: `Dashboard ${String(dashboard.id).slice(0, 8)} · ${table.technical_name||table.table_name}`,
        description: "Automatically managed by Dashboard Studio.",
        base_table: table.id,
        enabled: true,
      });
      const nextBindings = [...autoBindings, { table_id: table.id, model_id: created.id }];
      const nextLayout = { ...(dashboard.layout || {}), auto_semantic_models: nextBindings };
      const updated = await updateDashboard(dashboard.id, { layout: nextLayout });
      setDashboard((current) => ({ ...current, ...updated }));
      setModels((current) => [...current, created]);
      return created;
    } finally {
      setSemanticBusy(false);
    }
  }

  function dimensionType(field) {
    const type = String(field?.logical_type || "").toUpperCase();
    if (type.includes("DATE") && type.includes("TIME")) return "DATETIME";
    if (type.includes("DATE")) return "DATE";
    if (["INTEGER", "DECIMAL", "FLOAT", "NUMBER", "NUMERIC"].some((token) => type.includes(token))) return "NUMBER";
    if (["TEXT", "STRING", "CHAR"].some((token) => type.includes(token))) return "TEXT";
    return "CATEGORY";
  }

  async function ensureDimension(table, field) {
    if (!table || !field) return null;
    setSemanticBusy(true);
    setError("");
    try {
      const model = await ensureSemanticModel(table.id);
      const existing = (model?.dimensions || []).find((dimension) => String(dimension.field) === String(field.id));
      if (existing) return existing;
      const created = await createDimension({
        semantic_model: model.id,
        field: field.id,
        name: field.business_name || field.name,
        dimension_type: dimensionType(field),
        format: "",
        hierarchy: [],
        sort_order: (model.dimensions || []).length,
      });
      setModels((current) => current.map((entry) => String(entry.id) === String(model.id)
        ? { ...entry, dimensions: [...(entry.dimensions || []), created] }
        : entry));
      return created;
    } finally {
      setSemanticBusy(false);
    }
  }

  function isNumericField(field) {
    const type = String(field?.logical_type || "").toUpperCase();
    return ["INTEGER", "DECIMAL", "FLOAT", "NUMBER", "NUMERIC", "DOUBLE"].some((token) => type.includes(token));
  }

  async function createAutoMetric(table, field = null, aggregation = null) {
    const model = await ensureSemanticModel(table.id);
    const agg = aggregation || (field && isNumericField(field) ? "SUM" : "COUNT");
    const expression = field
      ? (agg === "DISTINCTCOUNT" ? `COUNT(DISTINCT {{field:${field.name}}})` : `${agg}({{field:${field.name}}})`)
      : "COUNT(*)";
    return createMetric({
      workspace: workspaceId,
      semantic_model: model.id,
      name: `__auto_visual__${field?.name || "rows"}_${agg}_${Date.now()}`,
      description: "Automatically managed visual binding.",
      expression_type: "SQL",
      source_field: null,
      aggregation: "NONE",
      expression,
      format_type: agg === "COUNT" || agg === "DISTINCTCOUNT" ? "INTEGER" : "NUMBER",
      unit: "",
      decimal_places: agg === "COUNT" || agg === "DISTINCTCOUNT" ? 0 : 2,
      enabled: true,
      cache_ttl_seconds: 60,
    });
  }

  function dragPayload(event) {
    try { return JSON.parse(event.dataTransfer.getData("application/x-bi-field") || event.dataTransfer.getData("text/plain")); }
    catch { return null; }
  }

  async function assignVisualBinding(slot, payload, aggregation = null) {
    if (!selectedItem || !selectedChart || !payload) return;
    setSaving(true);
    setError("");
    try {
      const currentBindings = selectedItem.config_override?.bindings || {};
      const nextBindings = { ...currentBindings };
      if (slot === "value") {
        if (payload.kind === "measure") {
          const metric = metrics.find((entry) => String(entry.id) === String(payload.metricId));
          if (!metric) throw new Error("Measure not found.");
          const axisModel = nextBindings.axis?.tableId ? modelForTable(nextBindings.axis.tableId) : null;
          const keepCategories = axisModel && String(axisModel.id) === String(metric.semantic_model);
          const keptDimensions = keepCategories ? [nextBindings.axis, nextBindings.legend].filter(Boolean).map((binding) => binding.dimensionId).filter(Boolean) : [];
          await updateChart(selectedChart.id, { metric: metric.id, dimensions: keptDimensions });
          nextBindings.value = { kind: "measure", metricId: metric.id, label: metric.name, tableId: payload.tableId || null };
          nextBindings.aggregation = null;
          if (!keepCategories) { nextBindings.axis = null; nextBindings.legend = null; }
        } else if (payload.kind === "field") {
          const table = tables.find((entry) => String(entry.id) === String(payload.tableId));
          const field = table?.fields?.find((entry) => String(entry.id) === String(payload.fieldId));
          if (!table || !field) throw new Error("Field not found.");
          const agg = aggregation || (isNumericField(field) ? "SUM" : "COUNT");
          const metric = await createAutoMetric(table, field, agg);
          const sameTable = !nextBindings.axis?.tableId || String(nextBindings.axis.tableId) === String(table.id);
          const keptDimensions = sameTable ? [nextBindings.axis, nextBindings.legend].filter(Boolean).map((binding) => binding.dimensionId).filter(Boolean) : [];
          await updateChart(selectedChart.id, { metric: metric.id, dimensions: keptDimensions });
          setMetrics((current) => [...current, metric]);
          nextBindings.value = { kind: "field", tableId: table.id, fieldId: field.id, fieldName: field.name, label: field.business_name || field.name };
          nextBindings.aggregation = agg;
          if (!sameTable) { nextBindings.axis = null; nextBindings.legend = null; }
        }
      } else if (["axis", "legend", "slicer"].includes(slot)) {
        if (payload.kind !== "field") throw new Error("Only table fields can be used as categorical fields.");
        const table = tables.find((entry) => String(entry.id) === String(payload.tableId));
        const field = table?.fields?.find((entry) => String(entry.id) === String(payload.fieldId));
        if (!table || !field) throw new Error("Field not found.");
        const dimension = await ensureDimension(table, field);
        const otherKey = slot === "legend" ? "axis" : "legend";
        const dimensionIds = [];
        const primary = slot === "slicer" ? null : nextBindings[otherKey];
        if (primary?.dimensionId) dimensionIds.push(primary.dimensionId);
        dimensionIds.push(dimension.id);
        await updateChart(selectedChart.id, { dimensions: dimensionIds });
        const binding = { kind: "field", tableId: table.id, fieldId: field.id, fieldName: field.name, label: field.business_name || field.name, dimensionId: dimension.id };
        if (slot === "slicer") nextBindings.axis = binding;
        else nextBindings[slot] = binding;
      }
      await patchItemConfig(selectedItem, { bindings: nextBindings }, true);
      await load({ quiet: true });
      setSelected(selectedItem.id);
      setTimeout(() => run(), 0);
    } catch (e) {
      setError(getApiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  async function changeVisualAggregation(nextAggregation) {
    const binding = selectedItem?.config_override?.bindings?.value;
    if (!binding || binding.kind !== "field") return;
    await assignVisualBinding("value", { kind: "field", tableId: binding.tableId, fieldId: binding.fieldId }, nextAggregation);
  }

  async function applySlicer(fieldName, value) {
    if (!fieldName) return;
    const without = runtimeFilters.filter((filter) => filter.field !== fieldName);
    const currently = runtimeFilters.find((filter) => filter.field === fieldName && filter.operator === "eq")?.value;
    const next = currently === value ? without : [...without, { field: fieldName, operator: "eq", value }];
    setRuntimeFilters(next);
    await run(next);
  }

  function insertMeasureField(table, field) {
    if (!table || !field) return;
    setActiveTableId(String(table.id));
    const token = measureLanguage === "SQL"
      ? `{{field:${field.name}}}`
      : measureLanguage === "DAX"
        ? `'${table.technical_name||table.table_name}'[${field.name}]`
        : `df["${field.name}"]`;
    setMeasureCode((current) => `${current}${current && !current.endsWith("\n") ? " " : ""}${token}`);
  }

  async function saveMeasure() {
    const expression = measureCode.trim();
    if (!activeTable) { setError("Select a table in the Data pane before creating a measure."); return; }
    if (!expression) { setError("Write the measure expression first."); return; }
    const stamp = new Date().toLocaleString([], {year:"numeric",month:"short",day:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit"});
    const name = `${measureLanguage} · ${activeTable.table_name} · ${stamp}`;
    setSemanticBusy(true);
    setError("");
    try {
      const model = await ensureSemanticModel(activeTable.id);
      const createdMetric = await createMetric({
        workspace: workspaceId,
        semantic_model: model.id,
        name,
        description: `${measureLanguage} measure created in Dashboard Studio`,
        expression_type: measureLanguage,
        source_field: null,
        aggregation: "NONE",
        expression,
        format_type: "NUMBER",
        unit: "",
        decimal_places: 2,
        enabled: true,
        cache_ttl_seconds: 60,
      });
      await createScriptBlock({workspace:workspaceId,name,language:measureLanguage,purpose:"",code:expression,context:{table_id:activeTable.id,table_name:activeTable.table_name,dashboard_id:dashboardId},linked_object_type:"METRIC",linked_object_id:createdMetric.id,status:"APPLIED"});
      setMeasureCode("");
      await load({ quiet: true });
      setMessage(`Measure ${name} created.`);
    } catch (e) {
      setError(getApiErrorMessage(e));
    } finally {
      setSemanticBusy(false);
    }
  }

  async function commitDashboardScript(){
    const code=(measureCode||"").trim(); if(!code)return; const lower=code.toLowerCase();
    const isChart=["plt.","sns.","matplotlib","seaborn","plotly","altair","chart(","bar(","line("].some(x=>lower.includes(x));
    const isFunction=measureLanguage==="PYTHON"&&/^\s*(async\s+)?def\s+/m.test(code);
    if(isChart){const upper=code.toUpperCase();const type=["LINE","AREA","PIE","DONUT","SCATTER","TABLE","KPI","BAR"].find(x=>upper.includes(x))||"BAR";await createVisual(type);await createScriptBlock({workspace:workspaceId,name:`Chart · ${new Date().toLocaleString()}`,language:measureLanguage,purpose:"",code,context:{table_id:activeTable?.id,dashboard_id:dashboardId,visual_type:type},status:"APPLIED"});setMeasureCode("");return;}
    if(isFunction){await createScriptBlock({workspace:workspaceId,name:`Function · ${new Date().toLocaleString()}`,language:measureLanguage,purpose:"",code,context:{dashboard_id:dashboardId,table_id:activeTable?.id},status:"SAVED"});setMeasureCode("");setMessage("Function registered in Scripts.");return;}
    return saveMeasure();
  }

  async function createVisual(type) {
    if (!canWrite || !effectivePageId) return;
    if (!activeTable) {
      setError("Select or open a table in Data before adding a visual.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const helperMetric = await createAutoMetric(activeTable, null, "COUNT");
      setMetrics((current) => [...current, helperMetric]);
      const backendType = type === "SLICER" ? "TABLE" : type;
      const chart = await createChart({
        workspace: workspaceId,
        name: `Untitled ${chartTypeLabel(type)}`,
        chart_type: backendType,
        metric: helperMetric.id,
        dimensions: [],
        config: {},
        default_filters: [],
        sort_order: [],
        limit: 500,
      });
      const created = await createDashboardItem({
        dashboard: dashboardId,
        chart: chart.id,
        title_override: "",
        position: nextPosition(pageItems),
        config_override: { page_id: effectivePageId, visual_type: type, style: DEFAULT_STYLE, bindings: {} },
      });
      await load({ quiet: true });
      setSelected(created.id);
      setVisualTab("build");
      setMessage(`${chartTypeLabel(type)} created and selected.`);
      setTimeout(() => run(), 0);
    } catch (e) {
      setError(getApiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  async function clearVisualBinding(slot) {
    if (!selectedItem || !selectedChart) return;
    setSaving(true);
    setError("");
    try {
      const nextBindings = { ...(selectedItem.config_override?.bindings || {}) };
      if (slot === "value") {
        delete nextBindings.value;
        delete nextBindings.aggregation;
        const tableId = nextBindings.axis?.tableId || nextBindings.legend?.tableId || activeTableId;
        const table = tables.find((entry) => String(entry.id) === String(tableId));
        if (!table) throw new Error("Select a table before clearing the value field.");
        const helperMetric = await createAutoMetric(table, null, "COUNT");
        setMetrics((current) => [...current, helperMetric]);
        const dimensions = [nextBindings.axis, nextBindings.legend].filter(Boolean).map((binding) => binding.dimensionId).filter(Boolean);
        await updateChart(selectedChart.id, { metric: helperMetric.id, dimensions });
      } else {
        const key = slot === "slicer" ? "axis" : slot;
        delete nextBindings[key];
        const dimensions = [nextBindings.axis, nextBindings.legend].filter(Boolean).map((binding) => binding.dimensionId).filter(Boolean);
        await updateChart(selectedChart.id, { dimensions });
      }
      await patchItemConfig(selectedItem, { bindings: nextBindings }, true);
      await load({ quiet: true });
      setSelected(selectedItem.id);
      setTimeout(() => run(), 0);
    } catch (e) {
      setError(getApiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  async function chooseVisualType(type) {
    if (selectedItem) {
      await patchItemConfig(selectedItem, { visual_type: type }, true);
      setVisualTab("build");
      return;
    }
    await createVisual(type);
  }

  function setManualZoom(next) {
    setCanvasZoomMode("manual");
    setCanvasZoom(clamp(next, 0.25, 2));
  }

  async function saveCanvasSettings(patch) {
    const current = dashboard?.layout || {};
    await saveDashboardMeta({ layout: { ...current, canvas: { ...(current.canvas || {}), ...patch } } });
  }

  async function removeItem(item) {
    if (!window.confirm(`¿Quitar “${item.title_override || item.chart_name || "visual"}” del dashboard?`)) return;
    setSaving(true);
    try {
      await deleteDashboardItem(item.id);
      if (String(selected) === String(item.id)) setSelected(null);
      setMessage("Visual eliminado del dashboard.");
      await load({ quiet: true });
      setTimeout(run, 0);
    } catch (e) {
      setError(getApiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  async function patchItem(item, payload, quiet = false) {
    try {
      await updateDashboardItem(item.id, payload);
      setDashboard((current) => ({
        ...current,
        items: (current.items || []).map((entry) => (String(entry.id) === String(item.id) ? { ...entry, ...payload } : entry)),
      }));
      if (!quiet) setMessage("Visual guardado.");
    } catch (e) {
      setError(getApiErrorMessage(e));
      await load({ quiet: true });
    }
  }

  async function patchItemConfig(item, patch, quiet = false) {
    const next = { ...(item.config_override || {}), ...patch };
    if (patch.style) next.style = { ...(item.config_override?.style || {}), ...patch.style };
    await patchItem(item, { config_override: next }, quiet);
  }

  async function saveTitle(item, title) {
    await patchItem(item, { title_override: title });
  }

  async function saveDashboardMeta(payload) {
    setSaving(true);
    try {
      const updated = await updateDashboard(dashboard.id, payload);
      setDashboard((current) => ({ ...current, ...updated }));
      setMessage("Dashboard guardado.");
    } catch (e) {
      setError(getApiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  async function savePages(nextPages) {
    const nextLayout = { ...(dashboard.layout || {}), pages: nextPages };
    await saveDashboardMeta({ layout: nextLayout });
  }

  async function addPage() {
    if (!canWrite) return;
    const next = { id: pageId(), name: `Page ${pages.length + 1}` };
    await savePages([...pages, next]);
    setActivePageId(next.id);
    setSelected(null);
  }

  async function commitPageRename(page) {
    const name = pageDraft.trim();
    setRenamingPage(null);
    if (!name || name === page.name) return;
    await savePages(pages.map((entry) => (entry.id === page.id ? { ...entry, name } : entry)));
  }

  async function deletePage(page) {
    if (pages.length === 1) return;
    const count = (dashboard.items || []).filter((item) => itemPage(item, pages[0].id) === page.id).length;
    if (!window.confirm(`Eliminar “${page.name}”${count ? ` y sus ${count} visual(es)` : ""}?`)) return;
    setSaving(true);
    try {
      const items = (dashboard.items || []).filter((item) => itemPage(item, pages[0].id) === page.id);
      await Promise.all(items.map((item) => deleteDashboardItem(item.id)));
      const nextPages = pages.filter((entry) => entry.id !== page.id);
      await updateDashboard(dashboard.id, { layout: { ...(dashboard.layout || {}), pages: nextPages } });
      setActivePageId(nextPages[0].id);
      setSelected(null);
      await load({ quiet: true });
      setMessage("Página eliminada.");
      setTimeout(run, 0);
    } catch (e) {
      setError(getApiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  async function updateSelectedChart(payload) {
    if (!selectedChart || !selectedItem) return;
    setSaving(true);
    setError("");
    try {
      await updateChart(selectedChart.id, payload);
      await load({ quiet: true });
      setMessage("Campos del visual actualizados.");
      setTimeout(run, 0);
    } catch (e) {
      setError(getApiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  async function chooseMetric(metric) {
    if (!selectedChart) return;
    const sameModel = String(metric.semantic_model) === String(selectedMetric?.semantic_model);
    await updateSelectedChart({ metric: metric.id, dimensions: sameModel ? selectedChart.dimensions || [] : [] });
  }

  function startGesture(e, item, type) {
    if (!editMode || !canWrite) return;
    e.preventDefault();
    e.stopPropagation();
    const el = canvasRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const p = pos(item.position);
    gesture.current = {
      id: item.id,
      type,
      startX: e.clientX,
      startY: e.clientY,
      p,
      cell: (rect.width - (COLS - 1) * GAP * canvasZoom) / COLS,
      scale: canvasZoom,
    };
    e.currentTarget.setPointerCapture?.(e.pointerId);
    setSelected(item.id);
  }

  function moveGesture(e) {
    const g = gesture.current;
    if (!g) return;
    const dx = Math.round((e.clientX - g.startX) / (g.cell + GAP * (g.scale || 1)));
    const dy = Math.round((e.clientY - g.startY) / ((ROW + GAP) * (g.scale || 1)));
    setDashboard((current) => ({
      ...current,
      items: current.items.map((item) => {
        if (String(item.id) !== String(g.id)) return item;
        let p = { ...g.p };
        if (g.type === "move") {
          p.x = clamp(g.p.x + dx, 0, COLS - g.p.w);
          p.y = Math.max(0, g.p.y + dy);
        } else {
          p.w = clamp(g.p.w + dx, 2, COLS - g.p.x);
          p.h = clamp(g.p.h + dy, 2, 12);
        }
        return { ...item, position: p };
      }),
    }));
  }

  async function endGesture() {
    const g = gesture.current;
    if (!g) return;
    gesture.current = null;
    const item = dashboard?.items?.find((entry) => String(entry.id) === String(g.id));
    if (item) await patchItem(item, { position: pos(item.position) }, true);
  }

  if (loading) return <Spinner label="Cargando dashboard..." />;
  if (!dashboard) return <Alert type="error">{error || "Dashboard no encontrado."}</Alert>;

  const maxRows = Math.max(
    8,
    ...pageItems.map((item, index) => {
      const p = pos(item.position, index);
      return p.y + p.h + 1;
    })
  );
  const canvasWidth = Number(dashboard?.layout?.canvas?.width) || 1280;
  const canvasHeight = Number(dashboard?.layout?.canvas?.height) || 720;
  const canvasContentHeight = Math.max(canvasHeight, maxRows * (ROW + GAP));
  const canvasStageStyle = { width: `${canvasWidth * canvasZoom}px`, height: `${canvasContentHeight * canvasZoom}px` };
  const scaledCanvasStyle = {
    ...canvasStyle(dashboard?.layout?.canvas),
    width: `${canvasWidth}px`,
    minWidth: `${canvasWidth}px`,
    height: `${canvasContentHeight}px`,
    minHeight: `${canvasContentHeight}px`,
    transform: `scale(${canvasZoom})`,
    transformOrigin: "top left",
  };

  return (
    <div className="dashboardStudio powerDashboardStudio">
      <header className="dashboardStudioBar powerDashboardTopbar">
        <div className="dashboardStudioIdentity">
          <Link href="/app/dashboards" className="iconTextButton dashboardBackIcon" aria-label="Back to dashboards" title="Back">←</Link>
          <div className="dashboardEditorContext">
            <strong>{draftMode ? "Dashboard canvas" : "Dashboard"}</strong>
            <span>{pages.find((page) => page.id === effectivePageId)?.name || "Page"}</span>
          </div>
        </div>
        <div className="dashboardStudioActions">
          {canWrite && editMode && <button type="button" className="button primaryButton smallButton" disabled={saving} onClick={async () => {
            const name = nameDraft.trim() || "Untitled dashboard";
            const nextLayout = { ...(dashboard.layout || {}), workspace_state: "SAVED" };
            await saveDashboardMeta({ name, layout: nextLayout });
            publishedRef.current = true;
            if (draftMode && onPublished) onPublished();
          }}>{saving ? "Saving..." : "Save"}</button>}
          {canWrite && (
            <button type="button" className={`button smallButton ${editMode ? "secondaryButton" : "primaryButton"}`} onClick={() => setEditMode((value) => !value)}>
              {editMode ? "Reading view" : "Edit"}
            </button>
          )}
          <button type="button" className="button secondaryButton smallButton" onClick={run} disabled={running || !dashboard.items?.length}>
            {running ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </header>

      {error && <Alert type="error">{error}</Alert>}
      {message && <div className="dashboardToast" onAnimationEnd={() => setMessage("")}>{message}</div>}

      {editMode && canWrite && (
        <ScriptWorkbench
          language={measureLanguage}
          onLanguage={setMeasureLanguage}
          code={measureCode}
          onCode={setMeasureCode}
          onCommit={commitDashboardScript}
          busy={semanticBusy}
          disabled={!activeTable}
        />
      )}


      <div className={`dashboardBuilderLayout powerDashboardLayout ${editMode ? "isEditing" : ""} ${editMode && rightOpen ? "rightOpen" : ""}`}>
        {editMode && canWrite && <aside className="analyticsVisualRail" aria-label="Visuals">{VISUAL_TYPES.map(type=><button key={type} type="button" title={chartTypeLabel(type)} aria-label={chartTypeLabel(type)} className={selectedItem && (selectedItem.config_override?.visual_type || selectedChart?.chart_type)===type?"active":""} disabled={saving || !tables.length} onClick={()=>chooseVisualType(type)}><VisualGlyph type={type}/></button>)}</aside>}
        <main ref={viewportRef} className="dashboardBuilderViewport powerDashboardViewport">
          <div className="canvasZoomToolbar" role="group" aria-label="Canvas zoom controls">
            <button type="button" onClick={() => setManualZoom(canvasZoom - 0.1)} aria-label="Zoom out">−</button>
            <button type="button" className="zoomPercent" onClick={() => setCanvasZoomMode("fit")} title="Fit canvas to viewport">{Math.round(canvasZoom * 100)}%</button>
            <button type="button" onClick={() => setManualZoom(canvasZoom + 0.1)} aria-label="Zoom in">+</button>
            <button type="button" className={canvasZoomMode === "fit" ? "active" : ""} onClick={() => setCanvasZoomMode("fit")}>Fit</button>
          </div>
          <div className="canvasZoomStage" style={canvasStageStyle}>
            {!pageItems.length ? (
              <div className="dashboardGridCanvas powerReportCanvas powerBlankCanvas" style={scaledCanvasStyle} onClick={() => setSelected(null)}>
                <div className="blankCanvasHint"><strong>Blank canvas</strong><span>Select a chart type in Visualizations to begin.</span></div>
              </div>
            ) : (
              <div
                ref={canvasRef}
                className="dashboardGridCanvas powerReportCanvas"
                style={scaledCanvasStyle}
                onPointerMove={moveGesture}
                onPointerUp={endGesture}
                onPointerCancel={endGesture}
                onClick={(e) => { if (e.target === e.currentTarget) setSelected(null); }}
              >
                {pageItems.map((item, index) => {
                  const p = pos(item.position, index);
                  const runtime = dataByItem.get(String(item.id));
                  const baseChart = runtime?.chart || chartMap.get(String(item.chart));
                  const style = itemStyle(item);
                  const visualType = item.config_override?.visual_type || baseChart?.chart_type || "TABLE";
                  const chart = baseChart ? { ...baseChart, chart_type: visualType } : baseChart;
                  const isSelected = String(selected) === String(item.id);
                  return (
                    <article
                      key={item.id}
                      className={`dashboardBuilderTile powerVisualTile ${isSelected ? "selected" : ""}`}
                      style={{
                        left: `calc(${(p.x / 12) * 100}% + ${p.x ? GAP / 2 : 0}px)`,
                        top: p.y * (ROW + GAP),
                        width: `calc(${(p.w / 12) * 100}% - ${GAP}px)`,
                        height: p.h * (ROW + GAP) - GAP,
                        background: style.backgroundColor,
                        borderColor: style.borderColor,
                        borderRadius: `${style.borderRadius}px`,
                        fontFamily: style.fontFamily,
                        color: style.textColor,
                      }}
                      onClick={() => editMode && setSelected(item.id)}
                    >
                      <header
                        className={`dashboardTileHandle ${style.showTitle ? "" : "titleHidden"}`}
                        style={{ color: style.titleColor, fontFamily: style.fontFamily }}
                        onPointerDown={(e) => startGesture(e, item, "move")}
                      >
                        <div>
                          {style.showTitle && (
                            <strong style={{ fontSize: style.titleFontSize, fontWeight: style.titleFontWeight }}>
                              {item.title_override || item.chart_name || chart?.name}
                            </strong>
                          )}
                          {editMode && <span>{chartTypeLabel(visualType)}</span>}
                        </div>
                        {editMode && <span className="dragHint">⋮⋮</span>}
                      </header>
                      <div className={`dashboardTileBody ${style.showTitle ? "" : "noTitle"}`}>
                        {running && !runtime ? <Spinner label="Loading..." /> : <ChartRenderer chart={chart} dataset={runtime?.dataset} title={item.title_override} visualStyle={style} visualType={visualType} slicerBinding={item.config_override?.bindings?.axis} activeSlicerValue={runtimeFilters.find((filter) => filter.field === item.config_override?.bindings?.axis?.fieldName)?.value} onSlicerSelect={applySlicer} />}
                      </div>
                      {editMode && <button type="button" className="dashboardResizeHandle" aria-label="Resize visual" onPointerDown={(e) => startGesture(e, item, "resize")}>⌟</button>}
                    </article>
                  );
                })}
              </div>
            )}
          </div>
        </main>

        {editMode && canWrite && (
          <aside className={`powerRightDock ${rightOpen ? "open" : "collapsed"}`}>
            <button type="button" className="powerDockToggle" aria-label={rightOpen ? "Collapse panels" : "Expand panels"} onClick={() => setRightOpen((value) => !value)}>
              {rightOpen ? "›" : "‹"}
            </button>
            {rightOpen && (
              <>
                <section className="powerVisualPane">
                  <div className="powerPaneHeader"><strong>Properties</strong></div>
                  <div className="powerPaneTabs">
                    <button type="button" className={visualTab === "build" ? "active" : ""} onClick={() => setVisualTab("build")}>Properties</button>
                    <button type="button" className={visualTab === "format" ? "active" : ""} onClick={() => setVisualTab("format")}>Format</button>
                  </div>
                  {visualTab === "build" ? (
                    <>
                      {selectedItem && (
                        <BuildVisualPanel
                          item={selectedItem}
                          chart={selectedChart}
                          metric={selectedMetric}
                          onDropBinding={assignVisualBinding}
                          onAggregation={changeVisualAggregation}
                          onClearBinding={clearVisualBinding}
                          onTitle={saveTitle}
                          onLimit={(limit) => updateSelectedChart({ limit })}
                          onRemove={removeItem}
                          saving={saving}
                        />
                      )}
                    </>
                  ) : selectedItem ? (
                    <FormatVisualPanel item={selectedItem} onChange={(patch) => patchItemConfig(selectedItem, { style: patch }, true)} />
                  ) : <CanvasFormatPanel canvas={dashboard?.layout?.canvas} onChange={saveCanvasSettings} />}
                </section>
                <section className="powerDataPane">
                  <div className="powerPaneHeader"><strong>Data</strong><span>{tables.length} tables</span></div>
                  <SharedDataPanel
                    tables={tables}
                    models={models}
                    metrics={dashboardMetrics}
                    activeTableId={activeTableId}
                    onTable={selectTable}
                    onField={insertMeasureField}
                    draggable
                    className="powerTableDataPane"
                    onMeasureDeleted={(id)=>setMetrics(current=>current.filter(metric=>String(metric.id)!==String(id)))}
                  />
                </section>
              </>
            )}
          </aside>
        )}
      </div>

      <footer className="reportPageTabs" aria-label="Dashboard pages">
        <div className="dashboardDocumentTabWrap">
          {canWrite && editMode ? (
            <input
              className="dashboardDocumentTabInput"
              value={nameDraft}
              aria-label="Dashboard name"
              onChange={(e) => setNameDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") e.currentTarget.blur(); }}
              onBlur={() => { const value = nameDraft.trim() || "Untitled dashboard"; setNameDraft(value); }}
            />
          ) : <span className="dashboardDocumentTabLabel">{dashboard.name}</span>}
        </div>
        <div className="reportPageTabsScroller">
          {pages.map((page) => (
            <div key={page.id} className={`reportPageTabWrap ${page.id === effectivePageId ? "active" : ""}`}>
              {renamingPage === page.id ? (
                <input
                  autoFocus
                  className="reportPageRename"
                  value={pageDraft}
                  onChange={(e) => setPageDraft(e.target.value)}
                  onBlur={() => commitPageRename(page)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") e.currentTarget.blur();
                    if (e.key === "Escape") setRenamingPage(null);
                  }}
                />
              ) : (
                <button
                  type="button"
                  className="reportPageTab"
                  onClick={() => { setActivePageId(page.id); setSelected(null); }}
                  onDoubleClick={() => { if (canWrite) { setRenamingPage(page.id); setPageDraft(page.name); } }}
                  title={canWrite ? "Double-click to rename" : page.name}
                >
                  {page.name}
                </button>
              )}
              {canWrite && pages.length > 1 && page.id === effectivePageId && (
                <button type="button" className="reportPageDelete" aria-label={`Delete ${page.name}`} onClick={() => deletePage(page)}>×</button>
              )}
            </div>
          ))}
          {canWrite && <button type="button" className="reportPageAdd" onClick={addPage} aria-label="Add page">+</button>}
        </div>
        <span className="reportPageHint">Double-click a page name to rename</span>
      </footer>
    </div>
  );
}

function BindingWell({ label, binding, accept = "field", onDrop, onClear, hint }) {
  return (
    <div className="powerFieldWell">
      <span>{label}</span>
      <div
        className={`fieldDropWell ${binding ? "hasBinding" : ""}`}
        onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = "copy"; }}
        onDrop={(event) => { event.preventDefault(); try { const payload = JSON.parse(event.dataTransfer.getData("application/x-bi-field") || event.dataTransfer.getData("text/plain")); onDrop(payload); } catch {} }}
      >
        {binding ? (
          <span className="bindingChip">
            <b>{binding.kind === "measure" ? "∑" : "◫"}</b>
            <span className="bindingChipLabel">{binding.label || binding.fieldName}</span>
            {onClear && <button type="button" className="bindingClearButton" aria-label={`Remove ${label}`} title="Remove field" onClick={(event) => { event.stopPropagation(); onClear(); }}>×</button>}
          </span>
        ) : <small>{hint || `Drag ${accept} here`}</small>}
      </div>
    </div>
  );
}

function BuildVisualPanel({ item, chart, metric, onDropBinding, onAggregation, onClearBinding, onTitle, onLimit, onRemove, saving }) {
  const [title, setTitle] = useState(item.title_override || "");
  useEffect(() => setTitle(item.title_override || ""), [item.id, item.title_override]);
  const type = item.config_override?.visual_type || chart?.chart_type || "TABLE";
  const bindings = item.config_override?.bindings || {};
  const valueBinding = bindings.value || (metric && !String(metric.name || "").startsWith("__auto_visual__") ? { kind: "measure", metricId: metric.id, label: metric.name } : null);
  const categoryLabel = type === "SLICER" ? "Field" : type === "KPI" ? "Category (optional)" : "X-axis / Category";
  return (
    <div className="powerPaneBody selectedVisualBuildPane">
      <div className="powerFieldWells">
        <BindingWell label={categoryLabel} binding={bindings.axis} onDrop={(payload) => onDropBinding(type === "SLICER" ? "slicer" : "axis", payload)} onClear={() => onClearBinding(type === "SLICER" ? "slicer" : "axis")} hint="Drag a field here" />
        {type !== "SLICER" && <BindingWell label={type === "KPI" ? "Value" : "Y-axis / Values"} binding={valueBinding} accept="field or measure" onDrop={(payload) => onDropBinding("value", payload)} onClear={() => onClearBinding("value")} hint="Drag a field or measure here" />}
        {!['KPI','SLICER','TABLE'].includes(type) && <BindingWell label="Legend" binding={bindings.legend} onDrop={(payload) => onDropBinding("legend", payload)} onClear={() => onClearBinding("legend")} hint="Drag a field here" />}
        {valueBinding?.kind === "field" && (
          <label className="powerCompactField">Aggregation
            <select value={bindings.aggregation || "SUM"} disabled={saving} onChange={(e) => onAggregation(e.target.value)}>
              <option value="SUM">Sum</option><option value="AVG">Average</option><option value="MIN">Minimum</option><option value="MAX">Maximum</option><option value="COUNT">Count</option><option value="DISTINCTCOUNT">Distinct count</option>
            </select>
          </label>
        )}
        <label className="powerCompactField">Title<input value={title} placeholder={item.chart_name || chart?.name} onChange={(e) => setTitle(e.target.value)} onBlur={() => title !== (item.title_override || "") && onTitle(item, title)} /></label>
        <label className="powerCompactField">Row limit<input type="number" min="1" max="5000" value={chart?.limit || 500} onChange={(e) => onLimit(Number(e.target.value) || 500)} /></label>
      </div>
      <p className="visualBindingHint">Drag Fields or Measures from Data. Raw fields are converted internally into the semantic binding required by the chart; you do not need to create a Dimension first.</p>
      <button type="button" className="button dangerButton smallButton" onClick={() => onRemove(item)}>Remove visual</button>
    </div>
  );
}

function FormatVisualPanel({ item, onChange }) {
  const style = itemStyle(item);
  return (
    <div className="powerPaneBody formatPaneBody">
      <FormatSection title="Title">
        <Toggle label="Show title" checked={style.showTitle} onChange={(value) => onChange({ showTitle: value })} />
        <ColorField label="Color" value={style.titleColor} onChange={(value) => onChange({ titleColor: value })} />
        <RangeField label="Size" min="9" max="32" value={style.titleFontSize} suffix="px" onChange={(value) => onChange({ titleFontSize: Number(value) })} />
        <label className="powerCompactField">Weight<select value={style.titleFontWeight} onChange={(e) => onChange({ titleFontWeight: Number(e.target.value) })}><option value="400">Regular</option><option value="500">Medium</option><option value="650">Semibold</option><option value="700">Bold</option></select></label>
      </FormatSection>
      <FormatSection title="Visual">
        <ColorField label="Data color" value={style.accentColor} onChange={(value) => onChange({ accentColor: value })} />
        <Toggle label="Legend" checked={style.showLegend} onChange={(value) => onChange({ showLegend: value })} />
        <Toggle label="Data labels" checked={style.showDataLabels} onChange={(value) => onChange({ showDataLabels: value })} />
        <Toggle label="Gridlines" checked={style.showGridlines} onChange={(value) => onChange({ showGridlines: value })} />
      </FormatSection>
      <FormatSection title="Text">
        <label className="powerCompactField">Font<select value={style.fontFamily} onChange={(e) => onChange({ fontFamily: e.target.value })}><option value="Inter, system-ui, sans-serif">Inter</option><option value="Arial, sans-serif">Arial</option><option value="Georgia, serif">Georgia</option><option value="'Segoe UI', sans-serif">Segoe UI</option><option value="'Courier New', monospace">Courier New</option></select></label>
        <ColorField label="Text color" value={style.textColor} onChange={(value) => onChange({ textColor: value })} />
        <RangeField label="Font size" min="9" max="24" value={style.fontSize} suffix="px" onChange={(value) => onChange({ fontSize: Number(value) })} />
      </FormatSection>
      <FormatSection title="Effects">
        <ColorField label="Background" value={style.backgroundColor} onChange={(value) => onChange({ backgroundColor: value })} />
        <ColorField label="Border" value={style.borderColor} onChange={(value) => onChange({ borderColor: value })} />
        <RangeField label="Corner radius" min="0" max="28" value={style.borderRadius} suffix="px" onChange={(value) => onChange({ borderRadius: Number(value) })} />
      </FormatSection>
    </div>
  );
}

function LegacyDataFieldsPanel({ tables, bindings, models, metrics, activeTableId, onTable, onInsertField }) {
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();
  const bindingFor = (tableId) => bindings.find((binding) => String(binding.table_id) === String(tableId));
  const modelFor = (tableId) => {
    const binding = bindingFor(tableId);
    return binding ? models.find((model) => String(model.id) === String(binding.model_id)) : null;
  };
  function beginDrag(event, payload) {
    const text = JSON.stringify(payload);
    event.dataTransfer.setData("application/x-bi-field", text);
    event.dataTransfer.setData("text/plain", text);
    event.dataTransfer.effectAllowed = "copy";
  }
  return (
    <div className="dataFieldsPanel powerTableDataPane">
      <div className="powerFieldSearch"><span>⌕</span><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search tables or fields" /></div>
      <div className="semanticTree tableSemanticTree">
        {tables.map((table) => {
          const model = modelFor(table.id);
          const tableMetrics = model ? metrics.filter((metric) => String(metric.semantic_model) === String(model.id)) : [];
          const fields = (table.fields || []).filter((field) => !q || field.name?.toLowerCase().includes(q) || field.business_name?.toLowerCase().includes(q));
          const visibleMetrics = tableMetrics.filter((metric) => !q || metric.name?.toLowerCase().includes(q));
          if (q && !fields.length && !visibleMetrics.length && !table.table_name?.toLowerCase().includes(q)) return null;
          return (
            <details key={table.id} open={String(activeTableId) === String(table.id) || Boolean(q)} onToggle={(e) => e.currentTarget.open && onTable(String(table.id))}>
              <summary onClick={() => onTable(String(table.id))}><span className="modelTreeIcon">▦</span><strong>{table.technical_name||table.table_name}</strong></summary>
              <div className="semanticTreeGroup rawFieldsGroup">
                <span className="semanticTreeLabel">Fields</span>
                {fields.map((field) => (
                  <button
                    key={field.id}
                    type="button"
                    className="powerDraggableField"
                    draggable
                    title="Drag into a visual field well; click to insert into the measure code editor"
                    onDragStart={(event) => beginDrag(event, { kind: "field", tableId: table.id, fieldId: field.id, fieldName: field.name, label: field.business_name || field.name, logicalType: field.logical_type })}
                    onClick={() => onInsertField(table, field)}
                  >
                    <span className="fieldTypeGlyph">{String(field.logical_type || "").toUpperCase().match(/NUMBER|INTEGER|DECIMAL|FLOAT/) ? "#" : "◫"}</span><span>{field.business_name || field.name}</span><span className="dragDots">⋮⋮</span>
                  </button>
                ))}
              </div>
              <div className="semanticTreeGroup">
                <span className="semanticTreeLabel">Measures</span>
                {visibleMetrics.length ? visibleMetrics.map((metric) => (
                  <button
                    key={metric.id}
                    type="button"
                    className="powerDraggableMeasure"
                    draggable
                    onDragStart={(event) => beginDrag(event, { kind: "measure", metricId: metric.id, tableId: table.id, semanticModelId: metric.semantic_model, label: metric.name })}
                    title="Drag into Values"
                  >
                    <span className="measureSigma">∑</span><span>{metric.name}</span><small>{metric.expression_type}</small><span className="dragDots">⋮⋮</span>
                  </button>
                )) : <span className="treeEmptyLabel">No measures yet</span>}
              </div>
            </details>
          );
        })}
      </div>
      <p className="powerDataHint">Drag Fields directly to Axis, Legend, Slicer or Values. Drag created Measures to Values. Dimensions are managed automatically and are no longer shown here.</p>
    </div>
  );
}

function FormatSection({ title, children }) {
  const [open, setOpen] = useState(true);
  return (
    <section className="formatSection">
      <button type="button" className="formatSectionHeader" onClick={() => setOpen((value) => !value)}><span>{open ? "⌄" : "›"}</span><strong>{title}</strong></button>
      {open && <div className="formatSectionBody">{children}</div>}
    </section>
  );
}
function Toggle({ label, checked, onChange }) {
  return <label className="powerToggleRow"><span>{label}</span><input type="checkbox" checked={Boolean(checked)} onChange={(e) => onChange(e.target.checked)} /></label>;
}
function ColorField({ label, value, onChange }) {
  return <label className="powerColorRow"><span>{label}</span><span className="powerColorControl"><input type="color" value={value || "#000000"} onChange={(e) => onChange(e.target.value)} /><input value={value || ""} onChange={(e) => onChange(e.target.value)} /></span></label>;
}
function RangeField({ label, min, max, value, suffix, onChange }) {
  return <label className="powerRangeRow"><span>{label}</span><span><input type="range" min={min} max={max} value={value} onChange={(e) => onChange(e.target.value)} /><output>{value}{suffix}</output></span></label>;
}

function CreateVisualPanel({ hasTables, selectedType, onChoose, saving }) {
  return (
    <div className="powerPaneBody createVisualPane">
      <div className="compactVisualTypeTitle"><strong>Visual type</strong></div>
      <div className="visualTypeGrid directVisualGrid">
        {VISUAL_TYPES.map((type) => <button key={type} type="button" className={selectedType === type ? "active" : ""} title={selectedType ? `Change selected visual to ${chartTypeLabel(type)}` : `Add ${chartTypeLabel(type)}`} disabled={saving || !hasTables} onClick={() => onChoose(type)}><VisualGlyph type={type} /><span>{chartTypeLabel(type)}</span></button>)}
      </div>
      {!hasTables && <p className="powerDataHint">Connect or import a table before creating visuals.</p>}
    </div>
  );
}

function CanvasFormatPanel({ canvas, onChange }) {
  const value = { kind: "dashboard", preset: "16:9", width: 1280, height: 720, background: "#ffffff", ...(canvas || {}) };
  const applyPreset = (preset) => {
    const presets = { "16:9": [1280,720], "4:3": [1024,768], "A4 portrait": [794,1123], "A4 landscape": [1123,794], "Letter portrait": [816,1056] };
    const size = presets[preset];
    onChange({ preset, width: size?.[0] || value.width, height: size?.[1] || value.height });
  };
  return <div className="powerPaneBody formatPaneBody">
    <FormatSection title="Canvas">
      <label className="powerCompactField">Type<select value={value.kind} onChange={(e) => onChange({ kind: e.target.value, preset: e.target.value === "report" ? "A4 portrait" : "16:9", width: e.target.value === "report" ? 794 : 1280, height: e.target.value === "report" ? 1123 : 720 })}><option value="dashboard">Dashboard</option><option value="report">Report</option></select></label>
      <label className="powerCompactField">Page size<select value={value.preset} onChange={(e) => applyPreset(e.target.value)}>{value.kind === "report" ? <><option>A4 portrait</option><option>A4 landscape</option><option>Letter portrait</option><option>Custom</option></> : <><option>16:9</option><option>4:3</option><option>Custom</option></>}</select></label>
      <div className="canvasSizeFields"><label>Width<input type="number" value={value.width} onChange={(e) => onChange({ preset:"Custom", width:Number(e.target.value) })}/></label><label>Height<input type="number" value={value.height} onChange={(e) => onChange({ preset:"Custom", height:Number(e.target.value) })}/></label></div>
      <ColorField label="Background" value={value.background} onChange={(background) => onChange({ background })} />
    </FormatSection>
  </div>;
}

function canvasStyle(canvas) {
  const value = { width:1280, height:720, background:"#ffffff", ...(canvas || {}) };
  return { width:`${value.width}px`, minWidth:`${value.width}px`, height:`${value.height}px`, minHeight:`${value.height}px`, background:value.background };
}
