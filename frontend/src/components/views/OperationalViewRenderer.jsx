"use client";

import { useEffect, useMemo, useState } from "react";

import Alert from "@/components/ui/Alert";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import { executeOperationalQuery, getViewData, interactWithView, operationalWriteback } from "@/lib/services/views";
import { getApiErrorMessage } from "@/lib/utils/errors";

function stringify(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function castValue(raw, logicalType) {
  if (["INTEGER", "BIGINT"].includes(logicalType)) return raw === "" ? null : Number.parseInt(raw, 10);
  if (["DECIMAL", "FLOAT"].includes(logicalType)) return raw === "" ? null : Number.parseFloat(raw);
  if (logicalType === "BOOLEAN") return ["true", "1", "yes", "si", "sí"].includes(String(raw).toLowerCase());
  if (logicalType === "JSON") {
    try { return JSON.parse(raw); } catch { return raw; }
  }
  return raw;
}

function firstBinding(schema, role) {
  return (schema.bindings || []).find((binding) => binding.role === role);
}

function visibleBindings(schema) {
  const bindings = (schema.bindings || []).filter((binding) => binding.role !== "HIDDEN");
  return bindings.length ? bindings : [];
}

function getRecordKey(row, schema) {
  const pk = schema.source_table?.primary_key || [];
  return pk.length === 1 ? row[pk[0]] : null;
}

function getVersion(row, schema) {
  return row[schema.source_table?.row_version_column || "__row_version"];
}

function TableLike({ schema, rows, canWrite, spreadsheet, onInteract }) {
  const bindings = visibleBindings(schema).filter((binding) => !["ROW", "COLUMN", "VALUE"].includes(binding.role));
  const display = bindings.length ? bindings : schema.bindings || [];

  async function editCell(row, binding) {
    if (!canWrite || !binding.editable) return;
    const recordKey = getRecordKey(row, schema);
    const version = getVersion(row, schema);
    if (recordKey === null || version === undefined) return;
    const raw = window.prompt(`Nuevo valor para ${binding.alias || binding.field}`, stringify(row[binding.field]));
    if (raw === null) return;
    await onInteract({
      action: spreadsheet ? "EDIT_CELL" : "UPDATE_FIELD",
      recordKey,
      expectedVersion: version,
      values: { [binding.field]: castValue(raw, binding.logical_type) },
    });
  }

  if (!display.length) return <EmptyState title="Sin bindings visibles" description="Agrega bindings DISPLAY u otros roles para mostrar columnas." />;
  return <div className="tableWrap"><table className="dataTable"><thead><tr>{display.map((binding) => <th key={binding.id}>{binding.alias || binding.field}<span className="bindingRoleMini">{binding.role}</span></th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={getRecordKey(row, schema) ?? index}>{display.map((binding) => <td key={binding.id} className={canWrite && binding.editable ? "editableCell" : ""} onDoubleClick={() => editCell(row, binding)} title={binding.editable ? "Doble clic para editar" : ""}>{stringify(row[binding.field]) || "—"}</td>)}</tr>)}</tbody></table></div>;
}

function Kanban({ schema, rows, canWrite, onInteract }) {
  const title = firstBinding(schema, "TITLE");
  const status = firstBinding(schema, "STATUS");
  const subtitle = firstBinding(schema, "SUBTITLE");
  const group = firstBinding(schema, "GROUP");
  const configured = Array.isArray(status?.options?.choices) ? status.options.choices : [];
  const statuses = [...new Set([...configured, ...rows.map((row) => row[status?.field]).filter((value) => value !== null && value !== undefined && value !== "")])];
  const [dragged, setDragged] = useState(null);

  if (!title || !status) return <EmptyState title="Kanban incompleto" description="Configura bindings TITLE y STATUS." />;
  if (!statuses.length) return <EmptyState title="Sin estados" description="Agrega registros con estado o define options.choices en el binding STATUS." />;

  async function drop(nextStatus) {
    if (!canWrite || !dragged || !status.editable) return;
    const recordKey = getRecordKey(dragged, schema);
    const version = getVersion(dragged, schema);
    if (recordKey === null || version === undefined || dragged[status.field] === nextStatus) return;
    await onInteract({ action: "MOVE_KANBAN", recordKey, expectedVersion: version, values: { [status.field]: nextStatus } });
    setDragged(null);
  }

  return <div className="kanbanBoard">{statuses.map((column) => <section className="kanbanColumn" key={String(column)} onDragOver={(e) => e.preventDefault()} onDrop={() => drop(column)}><header><strong>{stringify(column)}</strong><span>{rows.filter((row) => row[status.field] === column).length}</span></header><div className="kanbanCards">{rows.filter((row) => row[status.field] === column).map((row, index) => <article className="kanbanCard" key={getRecordKey(row, schema) ?? index} draggable={Boolean(canWrite && status.editable)} onDragStart={() => setDragged(row)}><strong>{stringify(row[title.field]) || "Sin título"}</strong>{subtitle && <p>{stringify(row[subtitle.field])}</p>}{group && <small>{stringify(row[group.field])}</small>}<small>v{getVersion(row, schema)}</small></article>)}</div></section>)}</div>;
}

function Matrix({ schema, rows, canWrite, onInteract }) {
  const rowBinding = firstBinding(schema, "ROW");
  const colBinding = firstBinding(schema, "COLUMN");
  const valueBinding = firstBinding(schema, "VALUE");
  if (!rowBinding || !colBinding || !valueBinding) return <EmptyState title="Matriz incompleta" description="Configura ROW, COLUMN y VALUE." />;
  const rowKeys = [...new Set(rows.map((row) => stringify(row[rowBinding.field])))];
  const colKeys = [...new Set(rows.map((row) => stringify(row[colBinding.field])))];
  const cellMap = new Map(rows.map((row) => [`${stringify(row[rowBinding.field])}::${stringify(row[colBinding.field])}`, row]));

  async function edit(row) {
    if (!row || !canWrite || !valueBinding.editable) return;
    const recordKey = getRecordKey(row, schema);
    const version = getVersion(row, schema);
    if (recordKey === null || version === undefined) return;
    const raw = window.prompt(`Nuevo valor para ${valueBinding.alias || valueBinding.field}`, stringify(row[valueBinding.field]));
    if (raw === null) return;
    await onInteract({ action: "EDIT_CELL", recordKey, expectedVersion: version, values: { [valueBinding.field]: castValue(raw, valueBinding.logical_type) } });
  }

  return <div className="tableWrap"><table className="dataTable matrixTable"><thead><tr><th>{rowBinding.alias || rowBinding.field}</th>{colKeys.map((column) => <th key={column}>{column || "—"}</th>)}</tr></thead><tbody>{rowKeys.map((rowKey) => <tr key={rowKey}><th>{rowKey || "—"}</th>{colKeys.map((colKey) => { const row = cellMap.get(`${rowKey}::${colKey}`); return <td key={colKey} className={row && canWrite && valueBinding.editable ? "editableCell" : ""} onDoubleClick={() => edit(row)}>{row ? stringify(row[valueBinding.field]) : "—"}</td>; })}</tr>)}</tbody></table></div>;
}

function FormView({ schema, rows, canWrite, onInteract }) {
  const pk = schema.source_table?.primary_key || [];
  const editable = (schema.bindings || []).filter((binding) => binding.editable && binding.role !== "HIDDEN");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const selected = rows[selectedIndex] || null;
  const [values, setValues] = useState({});

  useEffect(() => {
    if (!selected) return setValues({});
    const next = {};
    editable.forEach((binding) => { next[binding.field] = selected[binding.field] ?? ""; });
    setValues(next);
  }, [selectedIndex, rows, editable.map((b) => b.id).join("|")]);

  if (!editable.length) return <EmptyState title="Formulario incompleto" description="FORM requiere al menos un binding editable." />;
  if (!rows.length) return <EmptyState title="Sin registros" description="El backend de esta fase permite SUBMIT_FORM sobre registros existentes; crea registros desde Records Engine." />;

  async function submit(event) {
    event.preventDefault();
    const recordKey = getRecordKey(selected, schema);
    const version = getVersion(selected, schema);
    if (recordKey === null || version === undefined) return;
    const payload = {};
    editable.forEach((binding) => { payload[binding.field] = castValue(values[binding.field], binding.logical_type); });
    await onInteract({ action: "SUBMIT_FORM", recordKey, expectedVersion: version, values: payload });
  }

  return <div className="formViewLayout"><aside><label>Registro<select value={selectedIndex} onChange={(e) => setSelectedIndex(Number(e.target.value))}>{rows.map((row, index) => <option value={index} key={getRecordKey(row, schema) ?? index}>{pk.length === 1 ? `${pk[0]}=${stringify(row[pk[0]])}` : `Registro ${index + 1}`}</option>)}</select></label><p className="helperText">Versión {getVersion(selected, schema)}</p></aside><form className="card formStack" onSubmit={submit}>{editable.map((binding) => <label key={binding.id}>{binding.alias || binding.field}<input required={binding.required} disabled={!canWrite} value={stringify(values[binding.field])} onChange={(e) => setValues((current) => ({ ...current, [binding.field]: e.target.value }))} /></label>)}<button type="submit" className="button primaryButton" disabled={!canWrite}>Guardar formulario</button></form></div>;
}

function CalendarView({ schema, rows, canWrite, onInteract }) {
  const title = firstBinding(schema, "TITLE");
  const start = firstBinding(schema, "START_DATE");
  const end = firstBinding(schema, "END_DATE");
  if (!title || !start) return <EmptyState title="Calendario incompleto" description="Configura TITLE y START_DATE." />;
  const ordered = [...rows].sort((a, b) => String(a[start.field] || "").localeCompare(String(b[start.field] || "")));

  async function reschedule(row) {
    if (!canWrite || !start.editable) return;
    const newStart = window.prompt(`Nueva fecha/hora para ${start.alias || start.field}`, stringify(row[start.field]));
    if (newStart === null) return;
    const values = { [start.field]: newStart };
    if (end && end.editable) {
      const newEnd = window.prompt(`Nueva fecha/hora para ${end.alias || end.field}`, stringify(row[end.field]));
      if (newEnd !== null) values[end.field] = newEnd;
    }
    await onInteract({ action: "RESIZE_CALENDAR", recordKey: getRecordKey(row, schema), expectedVersion: getVersion(row, schema), values });
  }

  return <div className="calendarList">{ordered.map((row, index) => <article key={getRecordKey(row, schema) ?? index} className="calendarEvent"><time>{stringify(row[start.field]) || "Sin fecha"}</time><div><strong>{stringify(row[title.field]) || "Sin título"}</strong>{end && <p>Fin: {stringify(row[end.field]) || "—"}</p>}</div>{canWrite && start.editable && <button type="button" className="button secondaryButton smallButton" onClick={() => reschedule(row)}>Reprogramar</button>}</article>)}</div>;
}


function InlineFieldEditor({ edit, onCancel, onSave }) {
  const [draft, setDraft] = useState(edit?.value ?? "");
  useEffect(() => { setDraft(edit?.value ?? ""); }, [edit?.key]);
  if (!edit) return null;
  return <form className="ovInlineDataForm" onSubmit={async(e)=>{e.preventDefault();await onSave(draft)}}>
    <label><span>{edit.label}</span><input autoFocus value={draft} onChange={e=>setDraft(e.target.value)} /></label>
    <div><button type="button" className="button secondaryButton smallButton" onClick={onCancel}>Cancel</button><button type="submit" className="button primaryButton smallButton">Save</button></div>
  </form>;
}

function StudioRuntime({ ir, schema, rows, rowsByTable = {}, datasetsByComponent = {}, canWrite = false, onOqpWriteback }) {
  const [selectedByTable, setSelectedByTable] = useState({});
  const [filters, setFilters] = useState({});
  const [editing, setEditing] = useState(null);
  const byId = new Map((schema.bindings || []).map((b) => [String(b.field_id), b]));
  const sourceId=String(schema.source_table?.id||schema.source_table?.table_id||"");
  const refName=(r)=>r?.fieldName||byId.get(String(r?.fieldId))?.field||String(r?.fieldId||"");
  const rowsFor=(r)=>rowsByTable[String(r?.tableId)]||(String(r?.tableId)===sourceId?rows:[]);
  const selectedFor=(r)=>{const list=rowsFor(r);return list[selectedByTable[String(r?.tableId)]||0]||list[0]||null};
  const value=(r,row)=>{const name=refName(r);const table=r?.tableName;return row?.[table&&name?`${table}__${name}`:name] ?? row?.[name];};
  const beginEdit=(componentId,r,row)=>{if(!canWrite||!onOqpWriteback||!r||!row)return;const tid=String(r.tableId);const identity=row?.__row_identity?.[tid];const version=row?.__row_versions?.[tid];if(!identity||version===undefined||version===null)return;setEditing({key:`${componentId}:${tid}:${r.fieldId}`,componentId,ref:r,row,tableId:tid,identity,version,label:refName(r),value:stringify(value(r,row))})};
  const saveEdit=async(raw)=>{if(!editing)return;await onOqpWriteback({table_id:editing.tableId,field:refName(editing.ref),row_identity:editing.identity,expected_version:editing.version,value:raw});setEditing(null)};
  const components = ir?.components || [];
  if (!components.length) return <EmptyState title="Empty operational view" description="Add components in Design or Code." />;
  return <div className="ovRuntimeStudio ovRuntimeFree">
    {components.map((c) => {
      const p=c.position||{};const refs=Object.values(c.slots||{}).flatMap(v=>Array.isArray(v)?v:(v?[v]:[])).filter(Boolean);const first=refs[0];
      const componentRows=datasetsByComponent[String(c.id)]?.rows;const rawRows=Array.isArray(componentRows)?componentRows:(first?rowsFor(first):rows);const filterKey=first?String(first.tableId):sourceId;
      const activeFilters=filters[filterKey]||{};const filtered=rawRows.filter(row=>Object.entries(activeFilters).every(([f,v])=>!v||String(row[f]??"").toLowerCase().includes(String(v).toLowerCase())));const selected=first?(filtered[selectedByTable[filterKey]||0]||filtered[0]||null):null;
      const editor=editing?.componentId===c.id?<InlineFieldEditor edit={editing} onCancel={()=>setEditing(null)} onSave={saveEdit}/>:null;
      let body=null;
      if(c.type==="FILTER"){const r=c.slots?.field;const f=refName(r);body=<label className="ovRuntimeFilter"><span>{c.title}</span><input value={(filters[String(r?.tableId)]||{})[f]||""} placeholder={`Filter ${f}`} onChange={e=>{setFilters(x=>({...x,[String(r?.tableId)]:{...(x[String(r?.tableId)]||{}),[f]:e.target.value}}));setSelectedByTable(x=>({...x,[String(r?.tableId)]:0}))}}/></label>}
      else if(c.type==="TABLE"){const cols=c.slots?.columns||[];body=<div className="ovRuntimeBlock ovRuntimeCompact"><h3>{c.title}</h3><div className="tableWrap"><table className="dataTable"><thead><tr>{cols.map(r=><th key={`${r.tableId}:${r.fieldId}`}>{refName(r)}</th>)}</tr></thead><tbody>{filtered.slice(0,100).map((row,i)=><tr key={i} className={i===(selectedByTable[filterKey]||0)?"selectedRow":""} onClick={()=>setSelectedByTable(x=>({...x,[filterKey]:i}))}>{cols.map(r=><td key={`${r.tableId}:${r.fieldId}`} className={canWrite?"editableCell":""} title={canWrite?"Double-click to edit inside this component":""} onDoubleClick={e=>{e.stopPropagation();beginEdit(c.id,r,row)}}>{stringify(value(r,row))||"—"}</td>)}</tr>)}</tbody></table></div>{editor}</div>}
      else if(c.type==="DETAIL"||c.type==="FORM"){const fs=c.slots?.fields||[];body=<div className="ovRuntimeBlock ovRuntimeCompact"><h3>{c.title}</h3>{selected?<div className="ovDetailGrid">{fs.map(r=><div key={`${r.tableId}:${r.fieldId}`} className={canWrite?"ovEditableValue":""} onDoubleClick={()=>beginEdit(c.id,r,selected)}><small>{refName(r)}</small><strong>{stringify(value(r,selected))||"—"}</strong></div>)}</div>:<p>No selected row.</p>}{editor}</div>}
      else if(c.type==="METRIC"){const r=c.slots?.value;const row=selectedFor(r);body=<div className="ovRuntimeMetric ovRuntimeCompact" onDoubleClick={()=>beginEdit(c.id,r,row)}><small>{c.title}</small><strong>{row?stringify(value(r,row)):"—"}{c.props?.suffix?` ${c.props.suffix}`:""}</strong><span>{refName(r)}</span>{editor}</div>}
      else if(c.type==="ALERT"){const r=c.slots?.condition,row=selectedFor(r);body=Boolean(value(r,row))?<div className="ovRuntimeAlert ovRuntimeCompact" onDoubleClick={()=>beginEdit(c.id,r,row)}><strong>{c.title}</strong><span>{refName(r)}: {stringify(value(r,row))}</span>{editor}</div>:null}
      else if(c.type==="TEXT")body=<div className="ovRuntimeText">{c.props?.text||c.title}</div>;
      const naturalH=c.props?.manualHeight?(p.h||2):(c.type==="TABLE"?Math.max(2,Math.min(6,2+Math.ceil(Math.min(filtered.length,100)/8))):["METRIC","ALERT","FILTER","TEXT","BUTTON"].includes(c.type)?2:Math.max(2,Math.min(5,2+Math.ceil(refs.length/4))));
      return <section key={c.id} className="ovRuntimePositioned" style={{gridColumn:`${(p.x||0)+1} / span ${p.w||4}`,gridRow:`${(p.y||0)+1} / span ${naturalH}`}}>{body}</section>
    })}
  </div>;
}

export default function OperationalViewRenderer({ view, schema, canWrite }) {
  const defaultFilters = Array.isArray(view.default_filters) ? view.default_filters : [];
  const defaultOrder = Array.isArray(view.default_ordering) ? view.default_ordering[0] || "" : "";
  const [rows, setRows] = useState([]);
  const [rowsByTable, setRowsByTable] = useState({});
  const [datasetsByComponent, setDatasetsByComponent] = useState({});
  const [queryPlan, setQueryPlan] = useState(null);
  const [limit, setLimit] = useState(100);
  const [offset, setOffset] = useState(0);
  const [returned, setReturned] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const simplePk = (schema.source_table?.primary_key || []).length === 1;
  const writeEnabled = canWrite && simplePk;

  async function load(nextOffset = offset) {
    setIsLoading(true); setError("");
    try {
      const data = await getViewData(view.id, { limit, offset: nextOffset, orderBy: defaultOrder, filters: defaultFilters });
      setRows(data.rows || []); setReturned(data.returned || 0); setOffset(data.offset ?? nextOffset);
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
    finally { setIsLoading(false); }
  }

  useEffect(() => { load(0); }, [view.id, limit]);

  const builderIR = view?.config?.builder_ir || schema?.config?.builder_ir;
  useEffect(() => {
    let cancelled = false;
    async function loadOperationalDatasets() {
      if (!builderIR?.components?.length) { setDatasetsByComponent({}); setQueryPlan(null); return; }
      try {
        const result = await executeOperationalQuery(view.id, { limit: 100 });
        if (!cancelled) {
          setDatasetsByComponent(result.datasets || {});
          setQueryPlan(result.plan || null);
          const byTable = {};
          for (const component of builderIR.components || []) {
            const refs = Object.values(component.slots || {}).flatMap((v) => Array.isArray(v) ? v : (v ? [v] : []));
            const first = refs[0];
            const dataset = result.datasets?.[String(component.id)];
            if (first?.tableId && dataset?.rows && !byTable[String(first.tableId)]) byTable[String(first.tableId)] = dataset.rows;
          }
          setRowsByTable(byTable);
          const firstError = (result.errors || [])[0];
          if (firstError) setError(firstError.detail || "Operational Query Plan could not resolve a component.");
        }
      } catch (requestError) {
        if (!cancelled) setError(getApiErrorMessage(requestError));
      }
    }
    loadOperationalDatasets();
    return () => { cancelled = true; };
  }, [view.id, JSON.stringify(builderIR?.components || [])]);

  async function oqpWriteback(payload) {
    setError(""); setMessage("");
    try {
      await operationalWriteback(view.id, payload);
      setMessage("Governed writeback applied to the lineage-qualified source field.");
      const result = await executeOperationalQuery(view.id, { limit: 100 });
      setDatasetsByComponent(result.datasets || {});
      setQueryPlan(result.plan || null);
    } catch (requestError) { setError(getApiErrorMessage(requestError)); }
  }

  async function interact(payload) {
    setError(""); setMessage("");
    try {
      await interactWithView(view.id, payload);
      setMessage("Writeback aplicado correctamente.");
      await load();
    } catch (requestError) {
      const text = getApiErrorMessage(requestError);
      setError(requestError?.response?.status === 409 ? `${text} Recarga la vista: el registro o contrato pudo cambiar.` : text);
    }
  }

  if (!schema.contract?.valid && !builderIR?.components?.length) return <Alert type="error">La vista no cumple el contrato de bindings. Faltan: {(schema.contract?.missing_roles || []).join(", ") || schema.contract?.detail || "configuración requerida"}.</Alert>;

  const props = { schema, rows, canWrite: writeEnabled, onInteract: interact };
  let body = null;
  if (builderIR?.components?.length) body = <StudioRuntime ir={builderIR} schema={schema} rows={rows} rowsByTable={rowsByTable} datasetsByComponent={datasetsByComponent} canWrite={canWrite} onOqpWriteback={oqpWriteback} />;
  else if (view.view_type === "KANBAN") body = <Kanban {...props} />;
  else if (view.view_type === "MATRIX") body = <Matrix {...props} />;
  else if (view.view_type === "FORM") body = <FormView {...props} />;
  else if (view.view_type === "CALENDAR") body = <CalendarView {...props} />;
  else body = <TableLike {...props} spreadsheet={view.view_type === "SPREADSHEET"} />;

  return <div className="pageStack compactStack">
    {error && <Alert type="error">{error}</Alert>}{message && <Alert type="success">{message}</Alert>}
    {!simplePk && <Alert type="info">La tabla no tiene PK simple. La vista puede leer datos, pero el endpoint de interacción no puede hacer writeback por registro.</Alert>}
    <div className="viewRuntimeToolbar"><span>{builderIR?.components?.length ? `${Object.keys(datasetsByComponent).length} component dataset(s) · OQP ${queryPlan?.version || "…"}` : `${returned} registro(s) · offset ${offset}`}</span><div><select value={limit} onChange={(e) => { setLimit(Number(e.target.value)); setOffset(0); }}>{[25,50,100,250].map((value) => <option key={value}>{value}</option>)}</select><button type="button" className="button secondaryButton smallButton" disabled={offset === 0 || isLoading} onClick={() => load(Math.max(0, offset - limit))}>Anterior</button><button type="button" className="button secondaryButton smallButton" disabled={returned < limit || isLoading} onClick={() => load(offset + limit)}>Siguiente</button><button type="button" className="button secondaryButton smallButton" disabled={isLoading} onClick={() => load()}>Recargar</button></div></div>
    {isLoading ? <Spinner label="Cargando vista operacional..." /> : rows.length === 0 ? <EmptyState title="Sin datos" description="La tabla fuente no devolvió registros con la configuración actual." /> : body}
  </div>;
}
