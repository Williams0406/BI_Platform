"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import AnalyticsFilterBuilder, { normalizeAnalyticsFilters } from "@/components/analytics/AnalyticsFilterBuilder";
import ChartRenderer from "@/components/analytics/ChartRenderer";
import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Icon from "@/components/ui/Icon";
import Spinner from "@/components/ui/Spinner";
import WorkspaceCommandBar from "@/components/data/WorkspaceCommandBar";
import ScriptWorkbench from "@/components/data/ScriptWorkbench";
import SharedDataPanel from "@/components/data/SharedDataPanel";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { createChart, getChart, getDashboard, listCharts, updateChart } from "@/lib/services/analytics";
import { getCatalogTable, listCatalogTables } from "@/lib/services/dataModel";
import { listDataSources } from "@/lib/services/dataSources";
import { listSemanticModels, queryMetric } from "@/lib/services/metrics";
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
  KPI: [{ key: "value", label: "Value", kind: "measure", hint: "Measure" }],
  TABLE: [{ key: "rows", label: "Rows", kind: "dimension", hint: "Field" }, { key: "values", label: "Values", kind: "measure", hint: "Measure" }],
  BAR: [{ key: "category", label: "X-axis / Category", kind: "dimension", hint: "Field" }, { key: "value", label: "Y-axis / Values", kind: "measure", hint: "Measure" }, { key: "series", label: "Legend / Series", kind: "dimension", hint: "Field" }],
  HORIZONTAL_BAR: [{ key: "category", label: "Y-axis / Category", kind: "dimension", hint: "Field" }, { key: "value", label: "X-axis / Values", kind: "measure", hint: "Measure" }, { key: "series", label: "Legend / Series", kind: "dimension", hint: "Field" }],
  STACKED_BAR: [{ key: "category", label: "Axis", kind: "dimension", hint: "Field" }, { key: "value", label: "Values", kind: "measure", hint: "Measure" }, { key: "series", label: "Legend / Stack", kind: "dimension", hint: "Field" }],
  SIDE_BY_SIDE_BAR: [{ key: "category", label: "Axis", kind: "dimension", hint: "Field" }, { key: "value", label: "Values", kind: "measure", hint: "Measure" }, { key: "series", label: "Legend / Group", kind: "dimension", hint: "Field" }],
  LINE: [{ key: "x", label: "X-axis", kind: "dimension", hint: "Date or category" }, { key: "y", label: "Y-axis", kind: "measure", hint: "Measure" }, { key: "series", label: "Legend / Series", kind: "dimension", hint: "Optional field" }],
  DUAL_LINE: [{ key: "x", label: "Shared X-axis", kind: "dimension", hint: "Date or category" }, { key: "y", label: "Primary values", kind: "measure", hint: "Measure" }, { key: "series", label: "Series", kind: "dimension", hint: "Optional field" }],
  AREA: [{ key: "x", label: "X-axis", kind: "dimension", hint: "Date or category" }, { key: "y", label: "Y-axis / Values", kind: "measure", hint: "Measure" }, { key: "series", label: "Legend / Series", kind: "dimension", hint: "Optional field" }],
  PIE: [{ key: "legend", label: "Legend / Category", kind: "dimension", hint: "Field" }, { key: "values", label: "Values", kind: "measure", hint: "Measure" }],
  DONUT: [{ key: "legend", label: "Legend / Category", kind: "dimension", hint: "Field" }, { key: "values", label: "Values", kind: "measure", hint: "Measure" }],
  SCATTER: [{ key: "details", label: "Details", kind: "dimension", hint: "Field" }, { key: "x", label: "X-axis", kind: "measure", hint: "Measure" }, { key: "legend", label: "Legend", kind: "dimension", hint: "Optional field" }],
  CIRCLE: [{ key: "category", label: "Category", kind: "dimension", hint: "Field" }, { key: "size", label: "Size", kind: "measure", hint: "Measure" }],
  SIDE_BY_SIDE_CIRCLE: [{ key: "category", label: "Category", kind: "dimension", hint: "Field" }, { key: "size", label: "Size", kind: "measure", hint: "Measure" }, { key: "group", label: "Group", kind: "dimension", hint: "Field" }],
  HEATMAP: [{ key: "rows", label: "Rows", kind: "dimension", hint: "Field" }, { key: "columns", label: "Columns", kind: "dimension", hint: "Field" }, { key: "color", label: "Color / Value", kind: "measure", hint: "Measure" }],
  HIGHLIGHT_TABLE: [{ key: "rows", label: "Rows", kind: "dimension", hint: "Field" }, { key: "columns", label: "Columns", kind: "dimension", hint: "Field" }, { key: "color", label: "Color / Value", kind: "measure", hint: "Measure" }],
  TREEMAP: [{ key: "group", label: "Group", kind: "dimension", hint: "Field" }, { key: "size", label: "Size", kind: "measure", hint: "Measure" }, { key: "detail", label: "Details", kind: "dimension", hint: "Optional field" }],
  PACKED_BUBBLES: [{ key: "group", label: "Group", kind: "dimension", hint: "Field" }, { key: "size", label: "Size", kind: "measure", hint: "Measure" }],
  HISTOGRAM: [{ key: "bins", label: "Bins", kind: "dimension", hint: "Numeric field" }, { key: "frequency", label: "Frequency", kind: "measure", hint: "Measure" }],
  BOX_PLOT: [{ key: "category", label: "Category", kind: "dimension", hint: "Field" }, { key: "values", label: "Values", kind: "measure", hint: "Measure" }],
  GANTT: [{ key: "task", label: "Task", kind: "dimension", hint: "Field" }, { key: "duration", label: "Duration", kind: "measure", hint: "Measure" }, { key: "group", label: "Group", kind: "dimension", hint: "Optional field" }],
  BULLET: [{ key: "category", label: "Category", kind: "dimension", hint: "Field" }, { key: "actual", label: "Actual value", kind: "measure", hint: "Measure" }],
  SYMBOL_MAP: [{ key: "location", label: "Location", kind: "dimension", hint: "Geographic field" }, { key: "size", label: "Size", kind: "measure", hint: "Measure" }],
  FILLED_MAP: [{ key: "location", label: "Location", kind: "dimension", hint: "Geographic field" }, { key: "color", label: "Color saturation", kind: "measure", hint: "Measure" }],
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
  const [savedOpen, setSavedOpen] = useState(false);
  const [fieldSearch, setFieldSearch] = useState("");
  const [rightTab, setRightTab] = useState("properties");
  const [propertiesOpen,setPropertiesOpen]=useState(true);
  const [dataPanelOpen,setDataPanelOpen]=useState(true);
  const [visualFormat,setVisualFormat]=useState({title:true,subtitle:false,border:true,background:"#ffffff",fontSize:12,titleSize:14,legend:true,legendPosition:"bottom",xAxis:true,yAxis:true,gridlines:true,dataLabels:false,opacity:100,radius:0,shadow:false,padding:16});
  const [visualPosition,setVisualPosition]=useState({x:0,y:0});
  const [queryVersion, setQueryVersion] = useState(0);
  const [codeOpen,setCodeOpen]=useState(false);
  const [codeLanguage,setCodeLanguage]=useState("SQL");
  const [code,setCode]=useState("");
  const [readingView,setReadingView]=useState(false);
  const [visualSelected,setVisualSelected]=useState(false);
  const [reportName,setReportName]=useState("Untitled report");
  useEffect(()=>{if(!dashboardId)return;let live=true;getDashboard(dashboardId).then(d=>{if(live)setReportName(d?.name||"Untitled dashboard")}).catch(()=>{});return()=>{live=false}},[dashboardId]);
  const [pages,setPages]=useState([{id:"page-1",name:"Page 1",state:null}]);
  const [activePageId,setActivePageId]=useState("page-1");
  const [renamingPageId,setRenamingPageId]=useState(null);
  const [draggingVisual,setDraggingVisual]=useState(false);
  const dragOrigin=useRef(null);
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
      const tableGroups=await Promise.all(nextSources.map((source)=>listCatalogTables(source.id).catch(()=>[])));
      setTables(tableGroups.flatMap(listValue));
      const nextModels = listValue(modelsData).filter((item) => item.enabled !== false);
      setModels(nextModels);
      setCharts(listValue(chartsData));

      let definition = null;
      if (chartId) definition = await getChart(chartId);
      setSavedChart(definition);

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
    return {chartType,metricId,dimensionIds:[...dimensionIds],visualPosition:{...visualPosition},visualFormat:{...visualFormat},visualSelected};
  }

  function applyPageState(state){
    const next=state||{chartType:"KPI",metricId:"",dimensionIds:[],visualPosition:{x:0,y:0},visualFormat:{title:true,subtitle:false,border:true,background:"#ffffff",fontSize:12,titleSize:14,legend:true,legendPosition:"bottom",xAxis:true,yAxis:true,gridlines:true,dataLabels:false,opacity:100,radius:0,shadow:false,padding:16},visualSelected:false};
    setChartType(next.chartType||"KPI");setMetricId(next.metricId||"");setDimensionIds(next.dimensionIds||[]);setVisualPosition(next.visualPosition||{x:0,y:0});setVisualFormat(next.visualFormat||{title:true,border:true,background:"#ffffff",fontSize:12});setVisualSelected(Boolean(next.visualSelected));setDataset(null);
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

  function handleDrop(value, zone) {
    if (value.kind === "measure" && zone === "measure") {
      const nextMetricId=value.metricId || value.id;
      const owner=models.find((item)=>item.metrics?.some((candidate)=>String(candidate.id)===String(nextMetricId)));
      if(owner && String(owner.id)!==String(modelId)) setModelId(owner.id);
      selectMetric(nextMetricId);
    }
    if ((value.kind === "dimension" || value.kind === "field") && zone === "dimension") {
      const candidate=dimensions.find((item)=>String(item.id)===String(value.id)||String(item.field)===String(value.fieldId)||String(item.field_id)===String(value.fieldId)||String(item.field_name||item.name)===String(value.fieldName));
      if(candidate && !dimensionIds.includes(candidate.id)) {
        setDimensionIds((current) => [...current, candidate.id]);
        if (chartType === "KPI") setChartType("BAR");
      }
    }
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
      config: {},
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

  if (!models.length) {
    return (
      <div className="pageStack">
        <header className="pageHeader"><p className="eyebrow">Analyze</p><h1>Explore</h1><p>Explora métricas visualmente sin crear objetos intermedios antes de tiempo.</p></header>
        {error && <Alert type="error">{error}</Alert>}
        <EmptyState title="No hay modelos semánticos" description="Crea un Semantic Model y al menos una medida para comenzar a explorar." />
        <div className="formActions"><Link href="/app/data-table" className="button primaryButton">Open Data workspace</Link></div>
      </div>
    );
  }

  return (
    <div className="explorePage">

      {error && <Alert type="error">{error}</Alert>}
      {message && <Alert type="success">{message}</Alert>}
      <WorkspaceCommandBar view="analytics" codeOpen={codeOpen} onToggleCode={()=>setCodeOpen(v=>!v)} onSave={()=>{if(!saveName)setSaveName(savedChart?.name||`${metric?.name||"Analysis"} analysis`);setSaveOpen(true)}} onReading={()=>setReadingView(v=>!v)} onRefresh={()=>runQuery()}>
        <input className="analyticsReportName" value={reportName} onChange={e=>setReportName(e.target.value)} aria-label="Report name" title="Rename report" />
      </WorkspaceCommandBar>

      {savedOpen && (
        <section className="exploreSavedPanel">
          <div className="sectionHeading"><div><p className="eyebrow">Library</p><h2>Saved visuals</h2></div><button type="button" className="iconButton" onClick={() => setSavedOpen(false)} aria-label="Close"><Icon name="close" size={16} /></button></div>
          {charts.length ? <div className="exploreSavedGrid">{charts.slice(0, 12).map((item) => <Link key={item.id} href={`/app/analytics/${item.id}`}><span className="resourceIcon"><Icon name="chart" size={16} /></span><span><strong>{item.name}</strong><small>{item.chart_type} · {item.dimensions?.length || 0} dimension(s)</small></span></Link>)}</div> : <p className="mutedText">No saved visuals yet.</p>}
        </section>
      )}

      <div className={`exploreWorkspace tableauWorkspace ${readingView?"readingView":""} ${codeOpen?"codeOpen":""} ${propertiesOpen?"":"propertiesCollapsed"} ${dataPanelOpen?"":"dataCollapsed"}`}>
        <aside className="analyticsVisualRail" aria-label="Visuals">{CHART_TYPES.map(item=><button type="button" key={item.id} className={chartType===item.id&&visualSelected?"active":""} data-tooltip={item.label} aria-label={item.label} onClick={()=>{setChartType(item.id);setMetricId("");setDimensionIds([]);setDataset(null);setVisualPosition({x:0,y:0});setVisualSelected(true)}}><Icon name={item.icon} size={18}/></button>)}</aside>{!propertiesOpen&&<button type="button" className="analyticsCollapsedPanelButton properties" onClick={()=>setPropertiesOpen(true)}>Properties</button>}{!dataPanelOpen&&<button type="button" className="analyticsCollapsedPanelButton data" onClick={()=>setDataPanelOpen(true)}>Data</button>}
        {codeOpen&&<div className="analyticsWideCode"><ScriptWorkbench compact language={codeLanguage} onLanguage={setCodeLanguage} code={code} onCode={setCode} onCommit={()=>setMessage("Code block ready for execution integration.")} /></div>}
        <aside className="exploreDataPane analyticsSharedDataPane">
          <div className="explorePaneHeader"><strong>Data</strong><button type="button" className="panelCollapseButton" onClick={()=>setDataPanelOpen(false)} title="Collapse Data">›</button></div>
          <SharedDataPanel
            tables={tables}
            models={models}
            activeTableId={table?.id || ""}
            draggable
            onTable={(id)=>{const candidate=tables.find((item)=>String(item.id)===String(id));if(candidate)setTable(candidate)}}
            onField={()=>{}}
          />
        </aside>

        <main className="exploreCanvasPane">
          {visualSelected && <div className={`exploreCanvas analyticsVisualBlock selected ${running && !dataset ? "isLoading":""}`} tabIndex={0} style={{transform:`translate(${visualPosition.x}px, ${visualPosition.y}px)`,background:visualFormat.background,border:visualFormat.border?undefined:"0",fontSize:visualFormat.fontSize,borderRadius:visualFormat.radius,boxShadow:visualFormat.shadow?"0 8px 24px rgba(18,26,33,.12)":undefined,padding:visualFormat.padding,opacity:(visualFormat.opacity||100)/100}} onClick={(event)=>event.stopPropagation()} onMouseDown={(event)=>{if(event.button!==0||event.target.closest("button,input,select,textarea"))return;event.preventDefault();setDraggingVisual(true);dragOrigin.current={mouseX:event.clientX,mouseY:event.clientY,x:visualPosition.x,y:visualPosition.y}}} onMouseMove={(event)=>{if(!draggingVisual||!dragOrigin.current)return;setVisualPosition({x:dragOrigin.current.x+(event.clientX-dragOrigin.current.mouseX),y:dragOrigin.current.y+(event.clientY-dragOrigin.current.mouseY)})}} onMouseUp={()=>{setDraggingVisual(false);dragOrigin.current=null}} onMouseLeave={()=>{if(draggingVisual){setDraggingVisual(false);dragOrigin.current=null}}} onKeyDown={(event)=>{const step=event.shiftKey?10:2;if(event.key==="ArrowLeft"){event.preventDefault();setVisualPosition(p=>({...p,x:p.x-step}))}if(event.key==="ArrowRight"){event.preventDefault();setVisualPosition(p=>({...p,x:p.x+step}))}if(event.key==="ArrowUp"){event.preventDefault();setVisualPosition(p=>({...p,y:p.y-step}))}if(event.key==="ArrowDown"){event.preventDefault();setVisualPosition(p=>({...p,y:p.y+step}))}if((event.key==="Delete"||event.key==="Backspace")&&(event.ctrlKey||event.metaKey)){event.preventDefault();setVisualSelected(false);setMetricId("");setDimensionIds([]);setDataset(null)}}}>
            <button type="button" className="visualDeleteButton visualDeleteOnCanvas" title="Delete visual" aria-label="Delete visual" onMouseDown={e=>e.stopPropagation()} onClick={(e)=>{e.stopPropagation();setVisualSelected(false);setMetricId("");setDimensionIds([]);setDataset(null)}}><Icon name="close" size={15}/></button>
            {!metric ? <div className="exploreCanvasEmpty chartSpecificPlaceholder"><span className="emptyVisualIcon"><Icon name={CHART_TYPES.find(item=>item.id===chartType)?.icon||"chart"} size={30} /></span><strong>{CHART_TYPES.find(item=>item.id===chartType)?.label||"Visual"}</strong><span>Empty {CHART_TYPES.find(item=>item.id===chartType)?.label?.toLowerCase()||"visual"}. Drag fields and measures from Data into Properties to build it.</span></div> : running && !dataset ? <Spinner label="Querying measure..." /> : dataset ? <ChartRenderer chart={{ chart_type: chartType, name: savedChart?.name || metric.name }} dataset={dataset} /> : <div className="exploreCanvasEmpty"><strong>No result yet</strong><button type="button" className="button secondaryButton" onClick={() => runQuery()}>Run query</button></div>}
          </div>}
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
              {visualSelected && (VISUAL_PROPERTY_SLOTS[chartType] || VISUAL_PROPERTY_SLOTS.BAR).map((slot,index) => {
                const dimension = slot.kind === "dimension" ? selectedDimensions[index === 0 ? 0 : Math.min(index, selectedDimensions.length - 1)] : null;
                return <DropZone key={`${chartType}-${slot.key}`} label={slot.label} hint={slot.hint} emptyText={`Drop ${slot.hint.toLowerCase()}`} onDrop={(value) => handleDrop(value, slot.kind === "measure" ? "measure" : "dimension")}>
                  {slot.kind === "measure" && metric ? <button type="button" className="encodingPill measure" onClick={() => setMetricId("")}>{metric.name}<span>×</span></button> : null}
                  {slot.kind === "dimension" && dimension ? <button type="button" className="encodingPill" onClick={() => toggleDimension(dimension.id)}>{dimension.name}<span>×</span></button> : null}
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

      {saveOpen && <div className="modalBackdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setSaveOpen(false); }}><form className="modalCard exploreSaveModal" onSubmit={saveAnalysis}><div className="cardHeader"><div><p className="eyebrow">Persist analysis</p><h2>{savedChart ? "Update analysis" : "Save analysis"}</h2><p>The current visual, dimensions and filters become a reusable ChartDefinition.</p></div><button type="button" className="iconButton" onClick={() => setSaveOpen(false)}><Icon name="close" size={16} /></button></div><label>Name<input autoFocus value={saveName} onChange={(event) => setSaveName(event.target.value)} placeholder="e.g. Revenue by month" required /></label><div className="exploreSaveSummary"><span>{chartType}</span><span>{metric?.name}</span><span>{dimensionIds.length} dimension(s)</span><span>{filters.length} filter(s)</span></div><div className="formActions"><button type="button" className="button secondaryButton" onClick={() => setSaveOpen(false)}>Cancel</button><button type="submit" className="button primaryButton" disabled={saving || !saveName.trim()}>{saving ? "Saving..." : savedChart ? "Update analysis" : "Save analysis"}</button></div></form></div>}
    </div>
  );
}
