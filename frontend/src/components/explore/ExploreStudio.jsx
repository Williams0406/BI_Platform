"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import AnalyticsFilterBuilder, { normalizeAnalyticsFilters } from "@/components/analytics/AnalyticsFilterBuilder";
import ResizableVisual, {defaultVisualSize} from "@/components/analytics/ResizableVisual";
import ChartRenderer from "@/components/analytics/ChartRenderer";
import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Icon from "@/components/ui/Icon";
import Spinner from "@/components/ui/Spinner";
import WorkspaceCommandBar from "@/components/data/WorkspaceCommandBar";
import {createScriptBlock} from "@/lib/services/scripts";
import {useMeasureSelection} from "@/lib/hooks/useMeasureSelection";
import ScriptWorkbench from "@/components/data/ScriptWorkbench";
import SharedDataPanel from "@/components/data/SharedDataPanel";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { createChart, createDashboard, getChart, getDashboard, listCharts, updateChart, updateDashboard } from "@/lib/services/analytics";
import { getCatalogTable, listCatalogTables } from "@/lib/services/dataModel";
import { listDataSources } from "@/lib/services/dataSources";
import { createDimension, createMetric, createSemanticModel, listSemanticModels, queryMetric, updateMetric } from "@/lib/services/metrics";
import { getApiErrorMessage } from "@/lib/utils/errors";

const WRITE_ROLES = ["OWNER", "ADMIN", "BUILDER"];
const CHART_TYPES = [
  { id:"KPI", label:"KPI / Text", icon:"kpiChart" },
  { id:"TABLE", label:"Text table", icon:"textTableChart" },
  { id:"BAR", label:"Bars", icon:"verticalBarChart" },
  { id:"HORIZONTAL_BAR", label:"Horizontal bars", icon:"horizontalBarChart" },
  { id:"STACKED_BAR", label:"Stacked bars", icon:"stackedBarChart" },
  { id:"SIDE_BY_SIDE_BAR", label:"Side-by-side bars", icon:"sideBarChart" },
  { id:"LINE", label:"Line", icon:"lineChart" },
  { id:"DUAL_LINE", label:"Dual combination", icon:"dualLineChart" },
  { id:"AREA", label:"Area", icon:"areaChart" },
  { id:"PIE", label:"Pie", icon:"pieChart" },
  { id:"DONUT", label:"Donut", icon:"donutChart" },
  { id:"SCATTER", label:"Scatter plot", icon:"scatterChart" },
  { id:"CIRCLE", label:"Circle view", icon:"circleChart" },
  { id:"SIDE_BY_SIDE_CIRCLE", label:"Side-by-side circles", icon:"circleGridChart" },
  { id:"HEATMAP", label:"Heat map", icon:"heatmapChart" },
  { id:"HIGHLIGHT_TABLE", label:"Highlight table", icon:"highlightChart" },
  { id:"TREEMAP", label:"Treemap", icon:"treemapChart" },
  { id:"PACKED_BUBBLES", label:"Packed bubbles", icon:"bubbleChart" },
  { id:"HISTOGRAM", label:"Histogram", icon:"histogramChart" },
  { id:"BOX_PLOT", label:"Box-and-whisker plot", icon:"boxplotChart" },
  { id:"GANTT", label:"Gantt chart", icon:"ganttChart" },
  { id:"BULLET", label:"Bullet graph", icon:"bulletChart" },
  { id:"SYMBOL_MAP", label:"Symbol map", icon:"symbolMapChart" },
  { id:"FILLED_MAP", label:"Filled map", icon:"filledMapChart" },
 ];

const VISUAL_PROPERTY_SLOTS = {
  KPI: [{ key: "value", label: "Value", kind: "value", hint: "Field or measure" }],
  TABLE: [{ key: "rows", label: "Rows", kind: "dimension", hint: "Field" }, { key: "values", label: "Values", kind: "value", hint: "Field or measure" }],
  BAR: [{ key: "category", label: "X-axis / Category", kind: "dimension", hint: "Field" }, { key: "value", label: "Y-axis / Values", kind: "value", hint: "Field or measure" }, { key: "series", label: "Legend / Series", kind: "dimension", hint: "Field" }],
  HORIZONTAL_BAR: [{ key: "category", label: "Y-axis / Category", kind: "dimension", hint: "Field" }, { key: "value", label: "X-axis / Values", kind: "value", hint: "Field or measure" }, { key: "series", label: "Legend / Series", kind: "dimension", hint: "Field" }],
  STACKED_BAR: [{ key: "category", label: "Axis", kind: "dimension", hint: "Field" }, { key: "value", label: "Values", kind: "value", hint: "Field or measure" }, { key: "series", label: "Legend / Stack", kind: "dimension", hint: "Field" }],
  SIDE_BY_SIDE_BAR: [{ key: "category", label: "Axis", kind: "dimension", hint: "Field" }, { key: "value", label: "Values", kind: "value", hint: "Field or measure" }, { key: "series", label: "Legend / Group", kind: "dimension", hint: "Field" }],
  LINE: [{ key: "x", label: "X-axis", kind: "dimension", hint: "Date or category" }, { key: "y", label: "Y-axis", kind: "value", hint: "Field or measure" }, { key: "series", label: "Legend / Series", kind: "dimension", hint: "Optional field" }],
  DUAL_LINE: [{ key: "x", label: "Shared X-axis", kind: "dimension", hint: "Date or category" }, { key: "y", label: "Primary values", kind: "value", hint: "Field or measure" }, { key: "y2", label: "Secondary values", kind: "value", hint: "Field or measure" }, { key: "series", label: "Series", kind: "dimension", hint: "Optional field" }],
  AREA: [{ key: "x", label: "X-axis", kind: "dimension", hint: "Date or category" }, { key: "y", label: "Y-axis / Values", kind: "value", hint: "Field or measure" }, { key: "series", label: "Legend / Series", kind: "dimension", hint: "Optional field" }],
  PIE: [{ key: "legend", label: "Legend / Category", kind: "dimension", hint: "Field" }, { key: "values", label: "Values", kind: "value", hint: "Field or measure" }],
  DONUT: [{ key: "legend", label: "Legend / Category", kind: "dimension", hint: "Field" }, { key: "values", label: "Values", kind: "value", hint: "Field or measure" }],
  SCATTER: [{ key: "details", label: "Details", kind: "dimension", hint: "Field" }, { key: "x", label: "X-axis", kind: "value", hint: "Field or measure" }, { key: "y", label: "Y-axis", kind: "value", hint: "Field or measure" }, { key: "legend", label: "Legend", kind: "dimension", hint: "Optional field" }],
  CIRCLE: [{ key: "category", label: "Category", kind: "dimension", hint: "Field" }, { key: "size", label: "Size", kind: "value", hint: "Field or measure" }],
  SIDE_BY_SIDE_CIRCLE: [{ key: "category", label: "Category", kind: "dimension", hint: "Field" }, { key: "size", label: "Size", kind: "value", hint: "Field or measure" }, { key: "group", label: "Group", kind: "dimension", hint: "Field" }],
  HEATMAP: [{ key: "rows", label: "Rows", kind: "dimension", hint: "Field" }, { key: "columns", label: "Columns", kind: "dimension", hint: "Field" }, { key: "color", label: "Color / Value", kind: "value", hint: "Field or measure" }],
  HIGHLIGHT_TABLE: [{ key: "rows", label: "Rows", kind: "dimension", hint: "Field" }, { key: "columns", label: "Columns", kind: "dimension", hint: "Field" }, { key: "color", label: "Color / Value", kind: "value", hint: "Field or measure" }],
  TREEMAP: [{ key: "group", label: "Group", kind: "dimension", hint: "Field" }, { key: "size", label: "Size", kind: "value", hint: "Field or measure" }, { key: "detail", label: "Details", kind: "dimension", hint: "Optional field" }],
  PACKED_BUBBLES: [{ key: "group", label: "Group", kind: "dimension", hint: "Field" }, { key: "size", label: "Size", kind: "value", hint: "Field or measure" }],
  HISTOGRAM: [{ key: "bins", label: "Bins", kind: "dimension", hint: "Numeric field" }, { key: "frequency", label: "Frequency", kind: "value", hint: "Field or measure" }],
  BOX_PLOT: [{ key: "category", label: "Category", kind: "dimension", hint: "Field" }, { key: "values", label: "Values", kind: "value", hint: "Field or measure" }],
  GANTT: [{ key: "task", label: "Task", kind: "dimension", hint: "Field" }, { key: "duration", label: "Duration", kind: "value", hint: "Field or measure" }, { key: "group", label: "Group", kind: "dimension", hint: "Optional field" }],
  BULLET: [{ key: "category", label: "Category", kind: "dimension", hint: "Field" }, { key: "actual", label: "Actual value", kind: "value", hint: "Field or measure" }],
  SYMBOL_MAP: [{ key: "location", label: "Location", kind: "dimension", hint: "Geographic field" }, { key: "size", label: "Size", kind: "value", hint: "Field or measure" }],
  FILLED_MAP: [{ key: "location", label: "Location", kind: "dimension", hint: "Geographic field" }, { key: "color", label: "Color saturation", kind: "value", hint: "Field or measure" }],
};

function listValue(value) {
  return Array.isArray(value) ? value : value?.results || [];
}

function fieldLabel(item) {
  return item?.name || item?.field_name || "Field";
}

function recommendChart(dimensions) {
  return dimensions.length ? "BAR" : "KPI";
}

function FieldItem({ item, kind, selected, onClick }) {
  const isDimension = kind === "dimension";
  function dragStart(event) {
    event.dataTransfer.effectAllowed = "copy";
    event.dataTransfer.setData("application/x-bi-field", JSON.stringify({ kind, id: item.id }));
  }
  return (
    <button
      type="button"
      className={`exploreField ${selected ? "selected" : ""}`}
      draggable
      onDragStart={dragStart}
      onClick={onClick}
      title={isDimension ? item.field_name || item.name : item.description || item.name}
    >
      <span className="exploreFieldIcon"><Icon name={isDimension ? "catalog" : "measure"} size={14} /></span>
      <span className="exploreFieldIdentity">
        <strong>{fieldLabel(item)}</strong>
        <small>{isDimension ? item.logical_type || item.dimension_type || "Dimension" : item.aggregation || item.expression_type || "Measure"}</small>
      </span>
      {selected && <span className="exploreFieldCheck">✓</span>}
    </button>
  );
}

function DropZone({ label, hint, emptyText, children, onDrop, compact = false }) {
  const [over, setOver] = useState(false);
  return (
    <div
      className={`exploreDropZone ${compact ? "compact" : ""} ${over ? "isOver" : ""}`}
      onDragOver={(event) => { event.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setOver(false);
        try {
          const value = JSON.parse(event.dataTransfer.getData("application/x-bi-field"));
          onDrop?.(value);
        } catch {}
      }}
    >
      <div className="exploreDropHeader"><strong>{label}</strong>{hint && <span>{hint}</span>}</div>
      <div className="exploreDropContent">{children || <span className="exploreDropEmpty">{emptyText}</span>}</div>
    </div>
  );
}

export default function ExploreStudio({ chartId = null, dashboardId = null }) {
  const { activeWorkspace, organizations } = useWorkspace();
  const [models, setModels] = useState([]);
  const [tables, setTables] = useState([]);
  const [sources, setSources] = useState([]);
  const [charts, setCharts] = useState([]);
  const [modelId, setModelId] = useState("");
  const [metricId, setMetricId] = useState("");
  const [dimensionIds, setDimensionIds] = useState([]);
  const [chartType, setChartType] = useState("KPI");
  const [filters, setFilters] = useState([]);
  const [limit, setLimit] = useState(1000);
  const [useCache, setUseCache] = useState(true);
  const [table, setTable] = useState(null);
  const [dataset, setDataset] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [savedChart, setSavedChart] = useState(null);
  const [saveOpen, setSaveOpen] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [savedDashboardId,setSavedDashboardId]=useState(dashboardId || null);
  const [visualTooltip,setVisualTooltip]=useState(null);
  const [slotBindings,setSlotBindings]=useState({});
  const [savedOpen, setSavedOpen] = useState(false);
  const [fieldSearch, setFieldSearch] = useState("");
  const [rightTab, setRightTab] = useState("properties");
  const [propertiesOpen,setPropertiesOpen]=useState(true);
  const [dataPanelOpen,setDataPanelOpen]=useState(true);
  const [visualFormat,setVisualFormat]=useState({title:true,subtitle:false,border:true,background:"#ffffff",fontSize:12,titleSize:14,legend:true,legendPosition:"bottom",xAxis:true,yAxis:true,gridlines:true,dataLabels:false,opacity:100,radius:0,shadow:false,padding:16});
  const [visualSize,setVisualSize]=useState(null);
  const [visualPosition,setVisualPosition]=useState({x:0,y:0});
  const [queryVersion, setQueryVersion] = useState(0);
  const [codeOpen,setCodeOpen]=useState(false);
  const [codeLanguage,setCodeLanguage]=useState("SQL");
  const [code,setCode]=useState("");
  const [editingMeasureId,setEditingMeasureId]=useMeasureSelection(code,setCode);
  const [codeBusy,setCodeBusy]=useState(false);
  const [readingView,setReadingView]=useState(false);
  const [visualSelected,setVisualSelected]=useState(false);
  const [reportName,setReportName]=useState("Untitled report");
  useEffect(()=>{if(!dashboardId)return;let live=true;getDashboard(dashboardId).then(d=>{if(live){setReportName(d?.name||"Untitled dashboard");setSavedDashboardId(d?.id||dashboardId)}}).catch(()=>{});return()=>{live=false}},[dashboardId]);
  const [pages,setPages]=useState([{id:"page-1",name:"Page 1",state:null}]);
  const [activePageId,setActivePageId]=useState("page-1");
  const [renamingPageId,setRenamingPageId]=useState(null);


  const autoRunTimer = useRef(null);

  const organization = useMemo(
    () => organizations.find((item) => item.id === activeWorkspace?.organization),
    [organizations, activeWorkspace],
  );
  const canWrite = WRITE_ROLES.includes(organization?.current_user_role);
  const model = useMemo(() => models.find((item) => item.id === modelId), [models, modelId]);
  const metrics = model?.metrics || [];
  const dimensions = model?.dimensions || [];
  const metric = metrics.find((item) => item.id === metricId) || null;
  const selectedDimensions = dimensions.filter((item) => dimensionIds.includes(item.id));

  useEffect(()=>{const refresh=(event)=>{if(!event?.detail?.workspace||String(event.detail.workspace)===String(activeWorkspace?.id))loadBase()};window.addEventListener("bi-data-artifacts-changed",refresh);return()=>window.removeEventListener("bi-data-artifacts-changed",refresh)},[activeWorkspace?.id]);

  const filteredDimensions = useMemo(() => {
    const q = fieldSearch.trim().toLowerCase();
    if (!q) return dimensions;
    return dimensions.filter((item) => `${item.name} ${item.field_name || ""} ${item.logical_type || ""}`.toLowerCase().includes(q));
  }, [dimensions, fieldSearch]);
  const filteredMetrics = useMemo(() => {
    const q = fieldSearch.trim().toLowerCase();
    if (!q) return metrics;
    return metrics.filter((item) => `${item.name} ${item.description || ""} ${item.aggregation || ""}`.toLowerCase().includes(q));
  }, [metrics, fieldSearch]);

  async function loadBase() {
    if (!activeWorkspace?.id) { setLoading(false); return; }
    setLoading(true); setError("");
    try {
      const [modelsData, chartsData, sourceData] = await Promise.all([
        listSemanticModels(activeWorkspace.id),
        listCharts(activeWorkspace.id),
        listDataSources(activeWorkspace.id),
      ]);
      const nextSources=listValue(sourceData);
      setSources(nextSources);
      // Query the catalog by workspace, not only by the currently returned source list.
      // Derived SQL outputs are catalog assets too and must be visible immediately in Data.
      const workspaceTables=await listCatalogTables(null,"",activeWorkspace.id).catch(()=>[]);
      setTables(listValue(workspaceTables));
      const nextModels = listValue(modelsData).filter((item) => item.enabled !== false);
      setModels(nextModels);
      setCharts(listValue(chartsData));

      let definition = null;
      if (chartId) definition = await getChart(chartId);
      setSavedChart(definition);
      setVisualSize(definition?.config?.visualSize||null);
      setVisualPosition(definition?.config?.visualPosition||{x:0,y:0});

      const firstModelId = definition
        ? nextModels.find((item) => item.metrics?.some((candidate) => candidate.id === definition.metric))?.id
        : nextModels[0]?.id;
      const nextModel = nextModels.find((item) => item.id === firstModelId) || nextModels[0];
      setModelId(nextModel?.id || "");
      setMetricId(definition?.metric || nextModel?.metrics?.[0]?.id || "");
      setDimensionIds(definition?.dimensions || []);
      setChartType(definition?.chart_type || recommendChart(definition?.dimensions || []));
      setFilters((definition?.default_filters || []).map((item) => ({ ...item, value: Array.isArray(item.value) ? item.value.join(", ") : item.value })));
      setLimit(definition?.limit || 1000);
      setSaveName(definition?.name || "");
      setVisualSelected(Boolean(definition));
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadBase(); }, [activeWorkspace?.id, chartId]);

  useEffect(() => {
    setDataset(null);
    if (!model?.base_table) { setTable(null); return; }
    getCatalogTable(model.base_table).then(setTable).catch(() => setTable(null));
  }, [model?.base_table]);

  async function runQuery({ silent = false } = {}) {
    if (!metricId) { setDataset(null); return; }
    setRunning(true);
    if (!silent) setError("");
    try {
      const result = await queryMetric(metricId, {
        dimensions: dimensionIds,
        filters: normalizeAnalyticsFilters(filters),
        limit: Number(limit) || 1000,
        use_cache: useCache,
      });
      setDataset(result);
    } catch (requestError) {
      setDataset(null);
      setError(getApiErrorMessage(requestError));
    } finally {
      setRunning(false);
    }
  }

  useEffect(() => {
    if (!metricId || loading) return;
    clearTimeout(autoRunTimer.current);
    autoRunTimer.current = setTimeout(() => runQuery({ silent: true }), 380);
    return () => clearTimeout(autoRunTimer.current);
  }, [metricId, dimensionIds.join("|"), filters, limit, useCache, queryVersion, loading]);

  function selectModel(nextId) {
    const next = models.find((item) => item.id === nextId);
    setModelId(nextId);
    setMetricId(next?.metrics?.[0]?.id || "");
    setDimensionIds([]);
    setFilters([]);
    setChartType("KPI");
    setDataset(null);
    if (!chartId) { setSavedChart(null); setSaveName(""); }
  }

  function currentPageState(){
    return {chartType,metricId,dimensionIds:[...dimensionIds],slotBindings:{...slotBindings},visualPosition:{...visualPosition},visualSize:visualSize||defaultVisualSize(chartType),visualFormat:{...visualFormat},visualSelected};
  }

  function applyPageState(state){
    const next=state||{chartType:"KPI",metricId:"",dimensionIds:[],visualPosition:{x:0,y:0},visualFormat:{title:true,subtitle:false,border:true,background:"#ffffff",fontSize:12,titleSize:14,legend:true,legendPosition:"bottom",xAxis:true,yAxis:true,gridlines:true,dataLabels:false,opacity:100,radius:0,shadow:false,padding:16},visualSelected:false};
    setVisualSize(next.visualSize||null);setChartType(next.chartType||"KPI");setMetricId(next.metricId||"");setDimensionIds(next.dimensionIds||[]);setSlotBindings(next.slotBindings||{});setVisualPosition(next.visualPosition||{x:0,y:0});setVisualFormat(next.visualFormat||{title:true,border:true,background:"#ffffff",fontSize:12});setVisualSelected(Boolean(next.visualSelected));setDataset(null);
  }

  function switchPage(id){
    if(id===activePageId)return;
    const target=pages.find(page=>page.id===id);
    setPages(list=>list.map(page=>page.id===activePageId?{...page,state:currentPageState()}:page));
    setActivePageId(id);applyPageState(target?.state);
  }

  function addPage(){
    const id=`page-${Date.now()}`;
    setPages(list=>[...list.map(page=>page.id===activePageId?{...page,state:currentPageState()}:page),{id,name:`Page ${list.length+1}`,state:null}]);
    setActivePageId(id);applyPageState(null);
  }

  function selectMetric(nextMetricId) {
    setMetricId(nextMetricId);
    if (!dimensionIds.length) setChartType("KPI");
  }

  function toggleDimension(id) {
    setDimensionIds((current) => {
      const next = current.includes(id) ? current.filter((value) => value !== id) : [...current, id];
      if (!current.length && next.length && chartType === "KPI") setChartType("BAR");
      if (current.length && !next.length && ["BAR", "LINE", "AREA", "PIE", "DONUT", "SCATTER"].includes(chartType)) setChartType("KPI");
      return next;
    });
  }

  function dimensionTypeForField(value) {
    const logical=String(value?.logicalType || value?.logical_type || "").toUpperCase();
    if (["DATE"].includes(logical)) return "DATE";
    if (["DATETIME", "DATETIME_TZ", "TIMESTAMP"].includes(logical)) return "DATETIME";
    if (["INTEGER", "BIGINT", "DECIMAL", "FLOAT", "NUMBER"].includes(logical)) return "NUMBER";
    if (["TEXT", "STRING"].includes(logical)) return "TEXT";
    return "CATEGORY";
  }

  async function ensureFieldDimension(value) {
    const fieldId=value.fieldId || value.field_id || value.id;
    const tableId=value.tableId || value.table_id || table?.id;
    if(!fieldId || !tableId || !activeWorkspace?.id) return null;

    let owner=models.find((item)=>String(item.base_table)===String(tableId));
    if(!owner){
      const sourceTable=tables.find((item)=>String(item.id)===String(tableId));
      const baseName=sourceTable?.technical_name || sourceTable?.table_name || "Table";
      owner=await createSemanticModel({
        workspace:activeWorkspace.id,
        name:`${baseName} model`,
        description:"Created automatically from Analytics while assigning fields to a visual.",
        base_table:tableId,
        enabled:true,
      });
    }

    let candidate=(owner.dimensions || []).find((item)=>String(item.field)===String(fieldId));
    if(!candidate){
      candidate=await createDimension({
        semantic_model:owner.id,
        field:fieldId,
        name:value.label || value.fieldName || "Field",
        dimension_type:dimensionTypeForField(value),
        format:"",
        hierarchy:[],
        sort_order:(owner.dimensions || []).length,
      });
    }

    const refreshed=listValue(await listSemanticModels(activeWorkspace.id)).filter((item)=>item.enabled!==false);
    setModels(refreshed);
    const refreshedOwner=refreshed.find((item)=>String(item.id)===String(owner.id)) || owner;
    setModelId(refreshedOwner.id);
    return (refreshedOwner.dimensions || []).find((item)=>String(item.id)===String(candidate.id)) || candidate;
  }

  function isNumericFieldPayload(value) {
    const logical=String(value?.logicalType || value?.logical_type || "").toUpperCase();
    return ["INTEGER","BIGINT","SMALLINT","DECIMAL","FLOAT","DOUBLE","NUMBER","NUMERIC"].some((token)=>logical.includes(token));
  }

  function propertySlot(slotKey) {
    return (VISUAL_PROPERTY_SLOTS[chartType] || VISUAL_PROPERTY_SLOTS.BAR).find((slot)=>slot.key===slotKey) || null;
  }

  function isCategoricalSlot(slotKey) {
    const slot=propertySlot(slotKey);
    return slot?.kind === "dimension";
  }

  function fieldAggregationForSlot(value, slotKey) {
    // Raw numeric fields behave like Power BI implicit measures in Values.
    // Text/boolean fields are still useful in Values as a row count.
    if (isNumericFieldPayload(value)) return "SUM";
    return "COUNT";
  }

  async function createImplicitFieldMetric(value, slotKey) {
    const fieldId=value.fieldId || value.field_id || value.id;
    const tableId=value.tableId || value.table_id || table?.id;
    const sourceTable=tables.find((item)=>String(item.id)===String(tableId));
    const field=(sourceTable?.fields || []).find((item)=>String(item.id)===String(fieldId));
    if (!sourceTable || !field) throw new Error("The dropped field could not be resolved in Data.");
    let owner=models.find((item)=>String(item.base_table)===String(tableId));
    if(!owner){
      const baseName=sourceTable.technical_name || sourceTable.table_name || "Table";
      owner=await createSemanticModel({workspace:activeWorkspace.id,name:`${baseName} model`,description:"Created automatically from Analytics while assigning fields to a visual.",base_table:tableId,enabled:true});
    }
    const agg=fieldAggregationForSlot({...value,logicalType:field.logical_type},slotKey);
    const expression=agg==="COUNT" ? `COUNT({{field:${field.name}}})` : `${agg}({{field:${field.name}}})`;
    const created=await createMetric({workspace:activeWorkspace.id,semantic_model:owner.id,name:`__auto_visual__${field.name}_${agg}_${Date.now()}`,description:"Automatically managed visual binding.",expression_type:"SQL",source_field:null,aggregation:"NONE",expression,format_type:agg==="COUNT"?"INTEGER":"NUMBER",unit:"",decimal_places:agg==="COUNT"?0:2,enabled:true,cache_ttl_seconds:60});
    const refreshed=listValue(await listSemanticModels(activeWorkspace.id)).filter((item)=>item.enabled!==false);
    setModels(refreshed);
    setModelId(owner.id);
    return {metric:created,aggregation:agg,field};
  }

  async function handleDrop(value, slotKey) {
    const slot=propertySlot(slotKey);
    if (!slot || !value) return;
    setError("");

    // Category/legend/detail wells are semantic dimensions. A measure has no
    // row-level category to group by, so explain the mismatch instead of
    // silently moving it to Values.
    if (isCategoricalSlot(slotKey) && value.kind === "measure") {
      setError(`“${value.label || "This measure"}” is a measure and cannot be used in ${slot.label}. Use a field for this categorical role, or drop the measure into a value/axis role.`);
      return;
    }

    if (slot.kind === "value") {
      if (value.kind === "measure") {
        const nextMetricId=value.metricId || value.id;
        const owner=models.find((item)=>item.metrics?.some((candidate)=>String(candidate.id)===String(nextMetricId)));
        if (!owner) { setError("The selected measure is not available in the current semantic models."); return; }
        const changedModel=String(owner.id)!==String(modelId);
        if(changedModel){setModelId(owner.id);setDimensionIds([]);}
        setSlotBindings((current)=>({...Object.fromEntries(Object.entries(changedModel?{}:current).filter(([,binding])=>binding.kind!=="measure" || binding.slotKey!==slotKey)),[slotKey]:{kind:"measure",id:nextMetricId,label:value.label,slotKey}}));
        setMetricId(nextMetricId);
        return;
      }
      if (value.kind === "field" || value.kind === "dimension") {
        try {
          const implicit=await createImplicitFieldMetric(value,slotKey);
          setSlotBindings((current)=>({...current,[slotKey]:{kind:"field",id:value.fieldId || value.id,label:value.label || value.fieldName || implicit.field.name,metricId:implicit.metric.id,aggregation:implicit.aggregation,slotKey}}));
          setMetricId(implicit.metric.id);
          setMessage(`${implicit.field.business_name || implicit.field.name} added to ${slot.label} as ${implicit.aggregation}.`);
        } catch(requestError) { setError(getApiErrorMessage(requestError)); }
        return;
      }
      setError(`${slot.label} accepts a field or a measure.`);
      return;
    }

    if ((value.kind === "dimension" || value.kind === "field") && slot.kind === "dimension") {
      setSlotBindings((current)=>({...current,[slotKey]:{kind:"field",id:value.fieldId || value.id,label:value.label || value.fieldName || "Field"}}));
      try {
        let candidate=dimensions.find((item)=>String(item.id)===String(value.id)||String(item.field)===String(value.fieldId)||String(item.field_id)===String(value.fieldId)||String(item.field_name||item.name)===String(value.fieldName));
        if(!candidate && value.kind==="field") candidate=await ensureFieldDimension(value);
        if(!candidate) { setError(`${slot.label} requires a field that can be registered as a dimension.`); return; }
        setSlotBindings((current)=>({...current,[slotKey]:{kind:"dimension",id:candidate.id,label:candidate.name}}));
        setDimensionIds((current)=>current.some((id)=>String(id)===String(candidate.id)) ? current : [...current,candidate.id]);
        if(chartType==="KPI")setChartType("BAR");
      } catch(requestError) {
        setSlotBindings((current)=>{const next={...current};delete next[slotKey];return next});
        setError(getApiErrorMessage(requestError));
      }
      return;
    }

    setError(`${slot.label} does not accept this data item.`);
  }

  function clearSlot(slotKey) {
    const binding=slotBindings[slotKey];
    setSlotBindings(current=>{const next={...current};delete next[slotKey];return next});
    if(!binding)return;
    if(binding.kind==="measure" && String(metricId)===String(binding.id)) setMetricId("");
    if(binding.kind==="field" && binding.metricId && String(metricId)===String(binding.metricId)) setMetricId("");
    if(binding.kind==="dimension") {
      const usedElsewhere=Object.entries(slotBindings).some(([key,item])=>key!==slotKey&&item?.kind==="dimension"&&String(item.id)===String(binding.id));
      if(!usedElsewhere)setDimensionIds(current=>current.filter(id=>String(id)!==String(binding.id)));
    }
  }

  function metricEditorText(item) {
    if (!item) return "";
    const language=String(item.expression_type || "DAX").toUpperCase();
    if (language === "PYTHON") return item.expression || "";
    return `${item.name} = ${item.expression || ""}`;
  }

  function findMetricAcrossModels(metricIdValue) {
    for (const semantic of models) {
      const found=(semantic.metrics || []).find((item)=>String(item.id)===String(metricIdValue));
      if (found) return found;
    }
    return null;
  }

  function openMeasureInCode(item) {
    if (!item) return;
    setEditingMeasureId(item.id);
    const owner=models.find((semantic)=>(semantic.metrics || []).some((candidate)=>String(candidate.id)===String(item.id)));
    if (owner) {
      setModelId(owner.id);
      const ownerTable=tables.find((candidate)=>String(candidate.id)===String(owner.base_table));
      if (ownerTable) setTable(ownerTable);
    }
    setMetricId(item.id);
    setCodeLanguage(String(item.expression_type || "DAX").toUpperCase());
    setCode(metricEditorText(item));
    setCodeOpen(true);
    setMessage(`Editing measure: ${item.name}`);
  }

  function parseMeasureCode(raw, language) {
    const text=String(raw || "").trim();
    if (!text) throw new Error("Write a measure before running the code block.");
    const lang=String(language || "DAX").toUpperCase();
    if (lang === "PYTHON") {
      const nameMatch=text.match(/^\s*#\s*(?:measure|name)\s*:\s*(.+?)\s*$/im);
      const fallback=metric ? metric.name : "Python Measure";
      return {name:(nameMatch?.[1] || fallback).trim(), expression:text, expression_type:"PYTHON"};
    }
    const equals=text.indexOf("=");
    if (equals <= 0 || equals === text.length - 1) {
      throw new Error(`Use the format Measure Name = expression for ${lang}.`);
    }
    const name=text.slice(0,equals).trim();
    const expression=text.slice(equals+1).trim();
    if (!name || !expression) throw new Error("The measure needs both a name and an expression.");
    return {name,expression,expression_type:lang};
  }

  function referencedFieldNames(expression) {
    const text=String(expression || "");
    const names=new Set();
    for (const match of text.matchAll(/\[\s*([A-Za-z_][A-Za-z0-9_]*)\s*\]/g)) names.add(match[1]);
    const fn=/\b(?:COUNT|COUNTA|DISTINCTCOUNT|SUM|AVERAGE|AVG|MIN|MAX)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)/gi;
    for (const match of text.matchAll(fn)) names.add(match[1]);
    return [...names];
  }

  function resolveMeasureTable(parsed) {
    if (table?.id) return table;
    if (model?.base_table) {
      const current=tables.find((item)=>String(item.id)===String(model.base_table));
      if (current) return current;
    }
    const names=referencedFieldNames(parsed.expression).map((value)=>value.toLowerCase());
    if (names.length) {
      const matches=tables.filter((candidate)=>names.every((name)=>(candidate.fields || []).some((field)=>String(field.name).toLowerCase()===name)));
      if (matches.length === 1) return matches[0];
      if (matches.length > 1) throw new Error("The referenced fields exist in more than one table. Select the target table in Data first.");
    }
    if (tables.length === 1) return tables[0];
    throw new Error("Select the table that owns this measure in the Data panel first.");
  }

  async function commitMeasureCode() {
    if (!canWrite || codeBusy) return;
    setCodeBusy(true); setError(""); setMessage("");
    try {
      const parsed=parseMeasureCode(code,codeLanguage);
      const targetTable=resolveMeasureTable(parsed);
      let owner=models.find((item)=>String(item.base_table)===String(targetTable.id));
      if (!owner) {
        const baseName=targetTable.technical_name || targetTable.table_name || "Table";
        owner=await createSemanticModel({
          workspace:activeWorkspace.id,
          name:`${baseName} model`,
          description:"Created automatically from Analytics for reusable measures.",
          base_table:targetTable.id,
          enabled:true,
        });
      }
      const existing=models.flatMap((item)=>item.metrics || []).find((item)=>String(item.name).trim().toLowerCase()===parsed.name.toLowerCase());
      const payload={
        workspace:activeWorkspace.id,
        semantic_model:owner.id,
        name:parsed.name,
        description:existing?.description || "",
        expression_type:parsed.expression_type,
        source_field:null,
        aggregation:"NONE",
        expression:parsed.expression,
        format_type:existing?.format_type || "NUMBER",
        unit:existing?.unit || "",
        decimal_places:existing?.decimal_places ?? 2,
        enabled:true,
        cache_ttl_seconds:existing?.cache_ttl_seconds ?? 60,
      };
      const saved=existing ? await updateMetric(existing.id,payload) : await createMetric(payload);
      await createScriptBlock({workspace:activeWorkspace.id,name:saved.name,purpose:"MEASURE",language:codeLanguage,code,context:{table_id:targetTable.id},linked_object_type:"METRIC",linked_object_id:saved.id,status:"APPLIED"});
      const refreshed=listValue(await listSemanticModels(activeWorkspace.id)).filter((item)=>item.enabled!==false);
      setModels(refreshed);
      const refreshedOwner=refreshed.find((item)=>String(item.id)===String(saved.semantic_model));
      setModelId(refreshedOwner?.id || saved.semantic_model);
      setMetricId(saved.id);
      setTable(targetTable);
      setCode("");
      setMessage(existing ? `Measure “${saved.name}” updated.` : `Measure “${saved.name}” created.`);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setCodeBusy(false);
    }
  }

  async function saveDashboardDirectly() {
    if(!canWrite || !activeWorkspace?.id)return;
    const name=reportName.trim() || "Untitled report";
    setSaving(true);setError("");
    const layout={pages:pages.map(page=>page.id===activePageId?{...page,state:currentPageState()}:page),active_page_id:activePageId,workspace_state:"SAVED"};
    try {
      let saved;
      if(savedDashboardId){
        saved=await updateDashboard(savedDashboardId,{name,layout});
      }else{
        saved=await createDashboard({workspace:activeWorkspace.id,name,description:"",layout,global_filters:[]});
        setSavedDashboardId(saved.id);
      }
      setReportName(saved?.name || name);
      setMessage("Dashboard guardado.");
    }catch(requestError){setError(getApiErrorMessage(requestError))}finally{setSaving(false)}
  }

  async function saveAnalysis(event) {
    event.preventDefault();
    if (!canWrite || !metricId || !saveName.trim()) return;
    setSaving(true); setError("");
    const payload = {
      workspace: activeWorkspace.id,
      name: saveName.trim(),
      chart_type: chartType,
      metric: metricId,
      dimensions: dimensionIds,
      config: {...(savedChart?.config||{}),visualSize:visualSize||defaultVisualSize(chartType),visualPosition},
      default_filters: normalizeAnalyticsFilters(filters),
      sort_order: [],
      limit: Number(limit) || 1000,
    };
    try {
      let saved;
      if (savedChart?.id) {
        saved = await updateChart(savedChart.id, payload);
        setMessage("Análisis actualizado.");
      } else {
        saved = await createChart(payload);
        setMessage("Análisis guardado.");
      }
      setSavedChart(saved);
      setSaveName(saved.name);
      setSaveOpen(false);
      const data = await listCharts(activeWorkspace.id);
      setCharts(listValue(data));
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  if (!activeWorkspace) return <EmptyState title="Selecciona un workspace" description="Explore pertenece a un workspace." />;
  if (loading) return <Spinner label="Preparando Explore..." />;

  return (
    <div className="explorePage">

      {error && <Alert type="error">{error}</Alert>}
      {message && <Alert type="success">{message}</Alert>}
      {!models.length && <Alert type="info">Blank analytics workspace ready. Select a table from Data and use the code block to create reusable measures as you build the report.</Alert>}
      <WorkspaceCommandBar view="analytics" codeOpen={codeOpen} onToggleCode={()=>setCodeOpen(v=>!v)} onSave={saveDashboardDirectly} onReading={()=>setReadingView(v=>!v)} onRefresh={()=>runQuery()}>
        <input className="analyticsReportName" value={reportName} onChange={e=>setReportName(e.target.value)} aria-label="Report name" title="Rename report" />
      </WorkspaceCommandBar>

      {savedOpen && (
        <section className="exploreSavedPanel">
          <div className="sectionHeading"><div><p className="eyebrow">Library</p><h2>Saved visuals</h2></div><button type="button" className="iconButton" onClick={() => setSavedOpen(false)} aria-label="Close"><Icon name="close" size={16} /></button></div>
          {charts.length ? <div className="exploreSavedGrid">{charts.slice(0, 12).map((item) => <Link key={item.id} href={`/app/analytics/${item.id}`}><span className="resourceIcon"><Icon name="chart" size={16} /></span><span><strong>{item.name}</strong><small>{item.chart_type} · {item.dimensions?.length || 0} dimension(s)</small></span></Link>)}</div> : <p className="mutedText">No saved visuals yet.</p>}
        </section>
      )}

      <div className={`exploreWorkspace tableauWorkspace ${readingView?"readingView":""} ${codeOpen?"codeOpen":""} ${propertiesOpen?"":"propertiesCollapsed"} ${dataPanelOpen?"":"dataCollapsed"}`}>
        <aside className="analyticsVisualRail" aria-label="Visuals">{CHART_TYPES.map(item=><button type="button" key={item.id} className={chartType===item.id&&visualSelected?"active":""} aria-label={item.label} onMouseEnter={e=>{const r=e.currentTarget.getBoundingClientRect();setVisualTooltip({label:item.label,x:r.right+8,y:r.top+r.height/2})}} onMouseLeave={()=>setVisualTooltip(null)} onFocus={e=>{const r=e.currentTarget.getBoundingClientRect();setVisualTooltip({label:item.label,x:r.right+8,y:r.top+r.height/2})}} onBlur={()=>setVisualTooltip(null)} onClick={()=>{setVisualSize(null);setChartType(item.id);setMetricId("");setDimensionIds([]);setSlotBindings({});setDataset(null);setVisualPosition({x:0,y:0});setVisualSelected(true)}}><Icon name={item.icon} size={18}/></button>)}</aside>{visualTooltip&&<div className="analyticsVisualTooltip" role="tooltip" style={{left:visualTooltip.x,top:visualTooltip.y}}>{visualTooltip.label}</div>}{!propertiesOpen&&<button type="button" className="analyticsCollapsedPanelButton properties" onClick={()=>setPropertiesOpen(true)}>Properties</button>}{!dataPanelOpen&&<button type="button" className="analyticsCollapsedPanelButton data" onClick={()=>setDataPanelOpen(true)}>Data</button>}
        {codeOpen&&<div className="analyticsWideCode"><ScriptWorkbench metricId={editingMeasureId} compact language={codeLanguage} onLanguage={setCodeLanguage} code={code} onCode={setCode} onCommit={commitMeasureCode} busy={codeBusy} /></div>}
        <aside className="exploreDataPane analyticsSharedDataPane">
          <div className="explorePaneHeader unifiedPanelHeader"><div><strong>Data</strong><span>{table?.technical_name||table?.table_name||"No table selected"}</span></div><button type="button" className="panelCollapseButton" onClick={()=>setDataPanelOpen(false)} title="Collapse Data">›</button></div>
          <SharedDataPanel
            tables={tables}
            models={models}
            activeTableId={table?.id || ""}
            draggable
            onTable={(id)=>{const candidate=tables.find((item)=>String(item.id)===String(id));if(candidate)setTable(candidate)}}
            onField={()=>{}}
            onMeasure={openMeasureInCode}
            onMeasureDeleted={(id)=>{setModels(current=>current.map(item=>({...item,metrics:(item.metrics||[]).filter(metricItem=>String(metricItem.id)!==String(id))})));if(String(metricId)===String(id)){setMetricId("");setDataset(null)}}}
          />
        </aside>

        <main className="exploreCanvasPane">
          <div className="analyticsCanvasViewport"><div className="analyticsReportSurface">
          {visualSelected && <ResizableVisual className={`exploreCanvas analyticsVisualBlock selected ${running && !dataset ? "isLoading":""}`} tabIndex={0} position={visualPosition} size={visualSize||defaultVisualSize(chartType)} onPosition={setVisualPosition} onSize={setVisualSize} editable={canWrite&&!readingView} style={{background:visualFormat.background,border:visualFormat.border?undefined:"0",fontSize:visualFormat.fontSize,borderRadius:visualFormat.radius,boxShadow:visualFormat.shadow?"0 8px 24px rgba(18,26,33,.12)":undefined,padding:visualFormat.padding,opacity:(visualFormat.opacity||100)/100}} onKeyDown={event=>{if(event.target!==event.currentTarget||!canWrite||readingView)return;if((event.key==="Delete"||event.key==="Backspace")&&(event.ctrlKey||event.metaKey)){event.preventDefault();setVisualSelected(false);setMetricId("");setDimensionIds([]);setSlotBindings({});setDataset(null);return}const step=event.shiftKey?10:2;const size=visualSize||defaultVisualSize(chartType);if(["ArrowLeft","ArrowRight","ArrowUp","ArrowDown"].includes(event.key)){event.preventDefault();setVisualPosition(p=>({x:Math.max(0,Math.min(960-size.width,p.x+(event.key==="ArrowRight"?step:event.key==="ArrowLeft"?-step:0))),y:Math.max(0,Math.min(600-size.height,p.y+(event.key==="ArrowDown"?step:event.key==="ArrowUp"?-step:0)))}))}}}>
            <button type="button" className="visualDeleteButton visualDeleteOnCanvas" title="Delete visual" aria-label="Delete visual" onMouseDown={e=>e.stopPropagation()} onClick={(e)=>{e.stopPropagation();setVisualSelected(false);setMetricId("");setDimensionIds([]);setSlotBindings({});setDataset(null)}}><Icon name="close" size={15}/></button>
            {!metric ? <div className="exploreCanvasEmpty chartSpecificPlaceholder"><span className="emptyVisualIcon"><Icon name={CHART_TYPES.find(item=>item.id===chartType)?.icon||"chart"} size={30} /></span><strong>{CHART_TYPES.find(item=>item.id===chartType)?.label||"Visual"}</strong><span>Empty {CHART_TYPES.find(item=>item.id===chartType)?.label?.toLowerCase()||"visual"}. Drag fields and measures from Data into Properties to build it.</span></div> : running && !dataset ? <Spinner label="Querying measure..." /> : dataset ? <ChartRenderer chart={{ chart_type: chartType, name: savedChart?.name || metric.name }} dataset={dataset} /> : <div className="exploreCanvasEmpty"><strong>No result yet</strong><button type="button" className="button secondaryButton" onClick={() => runQuery()}>Run query</button></div>}
          </ResizableVisual>}
          </div></div>
          <div className="analyticsPageTabs" aria-label="Report pages">
            <div className="analyticsPageTabsScroller">{pages.map(page=><div key={page.id} className={`analyticsPageTab ${activePageId===page.id?"active":""}`} onClick={()=>switchPage(page.id)}>{renamingPageId===page.id?<input autoFocus value={page.name} onChange={e=>setPages(list=>list.map(item=>item.id===page.id?{...item,name:e.target.value}:item))} onBlur={()=>setRenamingPageId(null)} onKeyDown={e=>{if(e.key==="Enter"||e.key==="Escape")setRenamingPageId(null)}}/>:<button type="button" onDoubleClick={()=>setRenamingPageId(page.id)} title="Double-click to rename page">{page.name}</button>}</div>)}</div>
            <button type="button" className="analyticsAddPage" title="Add page" aria-label="Add page" onClick={addPage}><Icon name="plus" size={15}/></button>
          </div>
          <div className="exploreCanvasFooter"><span>Changes run automatically.</span><span>{table ? table.table_name : model?.name}</span></div>
        </main>

        <aside className={`explorePropertiesPane ${visualSelected?"":"noSelection"}`}>
          <div className="explorePropertiesTabs twoTabs"><button type="button" className="panelCollapseButton analyticsPanelCollapse" onClick={()=>setPropertiesOpen(false)} title="Collapse Properties">›</button>
            <button type="button" className={rightTab === "properties" ? "active" : ""} onClick={() => setRightTab("properties")}>Properties</button>
            <button type="button" className={rightTab === "format" ? "active" : ""} onClick={() => setRightTab("format")}>Format</button>
          </div>
          {rightTab === "properties" && <div className="explorePropertiesBody">
            <section className="propertySection"><div className="propertyTitle"><strong>{visualSelected ? (CHART_TYPES.find(item=>item.id===chartType)?.label||chartType) : "No visual selected"}</strong><span>{visualSelected ? "Drag fields and measures from Data into the specific roles for this chart." : "Choose a chart from the left rail to add it to the canvas."}</span></div>
              {visualSelected && (VISUAL_PROPERTY_SLOTS[chartType] || VISUAL_PROPERTY_SLOTS.BAR).map((slot) => {
                const binding=slotBindings[slot.key];
                const boundMeasure=binding?.kind==="measure" ? metrics.find(item=>String(item.id)===String(binding.id)) : null;
                const boundDimension=binding?.kind==="dimension" ? dimensions.find(item=>String(item.id)===String(binding.id)) : null;
                const pendingField=binding?.kind==="field" ? binding : null;
                return <DropZone key={`${chartType}-${slot.key}`} label={slot.label} hint={slot.hint} emptyText={`Drop ${slot.hint.toLowerCase()}`} onDrop={(value) => handleDrop(value, slot.key)}>
                  {boundMeasure ? <button type="button" className="encodingPill measure" onClick={() => clearSlot(slot.key)}>{boundMeasure.name}<span>×</span></button> : null}
                  {boundDimension ? <button type="button" className="encodingPill" onClick={() => clearSlot(slot.key)}>{boundDimension.name}<span>×</span></button> : null}
                  {pendingField ? <button type="button" className="encodingPill pending" onClick={() => clearSlot(slot.key)}>{pendingField.label}<span>×</span></button> : null}
                </DropZone>;
              })}
            </section>
          </div>}
          {rightTab === "format" && <div className="explorePropertiesBody analyticsFormatPanel">
            <section className="propertySection"><div className="propertyTitle"><strong>General</strong><span>Container and typography.</span></div>
              <label className="propertyCheck"><input type="checkbox" checked={visualFormat.title} onChange={e=>setVisualFormat(v=>({...v,title:e.target.checked}))}/> Show title</label>
              <label className="propertyCheck"><input type="checkbox" checked={visualFormat.subtitle} onChange={e=>setVisualFormat(v=>({...v,subtitle:e.target.checked}))}/> Show subtitle</label>
              <label className="propertyField">Title size<input type="number" min="10" max="36" value={visualFormat.titleSize} onChange={e=>setVisualFormat(v=>({...v,titleSize:Number(e.target.value)||14}))}/></label>
              <label className="propertyField">Content font size<input type="number" min="9" max="28" value={visualFormat.fontSize} onChange={e=>setVisualFormat(v=>({...v,fontSize:Number(e.target.value)||12}))}/></label>
            </section>
            <section className="propertySection"><div className="propertyTitle"><strong>Visual container</strong><span>Surface, spacing and effects.</span></div>
              <label className="propertyField">Background<input type="color" value={visualFormat.background} onChange={e=>setVisualFormat(v=>({...v,background:e.target.value}))}/></label>
              <label className="propertyField">Opacity <span>{visualFormat.opacity}%</span><input type="range" min="20" max="100" value={visualFormat.opacity} onChange={e=>setVisualFormat(v=>({...v,opacity:Number(e.target.value)}))}/></label>
              <label className="propertyCheck"><input type="checkbox" checked={visualFormat.border} onChange={e=>setVisualFormat(v=>({...v,border:e.target.checked}))}/> Border</label>
              <label className="propertyCheck"><input type="checkbox" checked={visualFormat.shadow} onChange={e=>setVisualFormat(v=>({...v,shadow:e.target.checked}))}/> Shadow</label>
              <label className="propertyField">Corner radius <span>{visualFormat.radius}px</span><input type="range" min="0" max="24" value={visualFormat.radius} onChange={e=>setVisualFormat(v=>({...v,radius:Number(e.target.value)}))}/></label>
              <label className="propertyField">Inner padding <span>{visualFormat.padding}px</span><input type="range" min="0" max="32" value={visualFormat.padding} onChange={e=>setVisualFormat(v=>({...v,padding:Number(e.target.value)}))}/></label>
            </section>
            <section className="propertySection"><div className="propertyTitle"><strong>Legend & labels</strong><span>Control supporting chart information.</span></div>
              <label className="propertyCheck"><input type="checkbox" checked={visualFormat.legend} onChange={e=>setVisualFormat(v=>({...v,legend:e.target.checked}))}/> Legend</label>
              <label className="propertyField">Legend position<select value={visualFormat.legendPosition} onChange={e=>setVisualFormat(v=>({...v,legendPosition:e.target.value}))}><option value="top">Top</option><option value="right">Right</option><option value="bottom">Bottom</option><option value="left">Left</option></select></label>
              <label className="propertyCheck"><input type="checkbox" checked={visualFormat.dataLabels} onChange={e=>setVisualFormat(v=>({...v,dataLabels:e.target.checked}))}/> Data labels</label>
            </section>
            <section className="propertySection"><div className="propertyTitle"><strong>Axes & grid</strong><span>Useful for Cartesian visuals.</span></div>
              <label className="propertyCheck"><input type="checkbox" checked={visualFormat.xAxis} onChange={e=>setVisualFormat(v=>({...v,xAxis:e.target.checked}))}/> X axis</label>
              <label className="propertyCheck"><input type="checkbox" checked={visualFormat.yAxis} onChange={e=>setVisualFormat(v=>({...v,yAxis:e.target.checked}))}/> Y axis</label>
              <label className="propertyCheck"><input type="checkbox" checked={visualFormat.gridlines} onChange={e=>setVisualFormat(v=>({...v,gridlines:e.target.checked}))}/> Gridlines</label>
            </section>
          </div>}
        </aside>
      </div>

    </div>
  );
}
