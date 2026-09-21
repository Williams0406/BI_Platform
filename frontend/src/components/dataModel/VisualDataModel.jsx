"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import Icon from "@/components/ui/Icon";

const NODE_WIDTH = 260;
const HEADER_HEIGHT = 48;
const FIELD_HEIGHT = 30;
const MAX_VISIBLE_FIELDS = 8;
const GRID_X = 330;
const GRID_Y = 330;

function tableLabel(table) {
  return table.technical_name || table.table_name;
}

function autoLayout(tables) {
  const columns = Math.max(1, Math.ceil(Math.sqrt(tables.length)));
  return Object.fromEntries(
    tables.map((table, index) => [
      table.id,
      {
        x: 56 + (index % columns) * GRID_X,
        y: 56 + Math.floor(index / columns) * GRID_Y,
      },
    ]),
  );
}

function getNodeHeight(table, compact = false) {
  if (compact) return HEADER_HEIGHT + 8;
  const visible = Math.min(table.fields?.length || 0, MAX_VISIBLE_FIELDS);
  return HEADER_HEIGHT + visible * FIELD_HEIGHT + ((table.fields?.length || 0) > MAX_VISIBLE_FIELDS ? 30 : 8);
}

function relationPath(source, target, sourceHeight, targetHeight) {
  const sx = source.x + NODE_WIDTH;
  const sy = source.y + Math.min(sourceHeight * 0.48, 132);
  const tx = target.x;
  const ty = target.y + Math.min(targetHeight * 0.48, 132);
  const delta = Math.max(70, Math.abs(tx - sx) * 0.45);
  return `M ${sx} ${sy} C ${sx + delta} ${sy}, ${tx - delta} ${ty}, ${tx} ${ty}`;
}

export default function VisualDataModel({ workspaceId, tables, relations, sources, selectedId, onSelect, onRenameTable, onDeleteTable, onDeleteSource, compactRelationships = false, query = "", sourceFilter = "ALL" }) {
  const viewportRef = useRef(null);
  const dragRef = useRef(null);
  const [positions, setPositions] = useState(() => autoLayout(tables));
  const [zoom, setZoom] = useState(1);
  const [editingTable, setEditingTable] = useState(null);
  const [editingName, setEditingName] = useState("");

  const storageKey = workspaceId ? `bi:model-layout:${workspaceId}` : "";

  useEffect(() => {
    const generated = autoLayout(tables);
    if (!storageKey) { setPositions(generated); return; }
    try {
      const saved = JSON.parse(window.localStorage.getItem(storageKey) || "{}");
      setPositions(Object.fromEntries(tables.map((table) => [table.id, saved[table.id] || generated[table.id]])));
    } catch {
      setPositions(generated);
    }
  }, [storageKey, tables]);

  useEffect(() => {
    if (!storageKey || Object.keys(positions).length === 0) return;
    window.localStorage.setItem(storageKey, JSON.stringify(positions));
  }, [positions, storageKey]);

  const sourceById = useMemo(() => Object.fromEntries(sources.map((source) => [source.id, source])), [sources]);
  const tableById = useMemo(() => Object.fromEntries(tables.map((table) => [table.id, table])), [tables]);

  const visibleTables = useMemo(() => {
    const term = query.trim().toLowerCase();
    return tables.filter((table) => {
      const source = sourceById[table.data_source];
      const matchesSource = sourceFilter === "ALL" || table.data_source === sourceFilter;
      const matchesQuery = !term || tableLabel(table).toLowerCase().includes(term) || (table.fields || []).some((field) => `${field.name} ${field.business_name || ""}`.toLowerCase().includes(term));
      return matchesSource && matchesQuery;
    });
  }, [tables, query, sourceFilter, sourceById]);

  const visibleIds = useMemo(() => new Set(visibleTables.map((table) => table.id)), [visibleTables]);
  const visibleRelations = useMemo(() => relations.filter((relation) => visibleIds.has(relation.source_table) && visibleIds.has(relation.target_table)), [relations, visibleIds]);

  const canvasSize = useMemo(() => {
    const nodes = visibleTables.map((table) => ({ table, pos: positions[table.id] || { x: 0, y: 0 } }));
    const maxX = nodes.reduce((acc, item) => Math.max(acc, item.pos.x + NODE_WIDTH + 120), 1000);
    const maxY = nodes.reduce((acc, item) => Math.max(acc, item.pos.y + getNodeHeight(item.table, compactRelationships) + 120), 680);
    return { width: Math.max(1100, maxX), height: Math.max(680, maxY) };
  }, [visibleTables, positions, compactRelationships]);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return undefined;
    function onKeyDown(event) {
      if (!(event.ctrlKey || event.metaKey)) return;
      if (["+", "=", "-", "0"].includes(event.key)) event.preventDefault();
      if (event.key === "+" || event.key === "=") setZoom((value) => Math.min(1.5, +(value + .1).toFixed(2)));
      if (event.key === "-") setZoom((value) => Math.max(.55, +(value - .1).toFixed(2)));
      if (event.key === "0") setZoom(1);
    }
    function onWheel(event) {
      if (!(event.ctrlKey || event.metaKey)) return;
      event.preventDefault();
      setZoom((value) => Math.min(1.5, Math.max(.55, +(value + (event.deltaY < 0 ? .1 : -.1)).toFixed(2))));
    }
    viewport.addEventListener("keydown", onKeyDown);
    viewport.addEventListener("wheel", onWheel, { passive: false });
    return () => { viewport.removeEventListener("keydown", onKeyDown); viewport.removeEventListener("wheel", onWheel); };
  }, []);

  function beginDrag(event, tableId) {
    if (event.button !== 0) return;
    const start = positions[tableId] || { x: 0, y: 0 };
    dragRef.current = { tableId, startX: event.clientX, startY: event.clientY, x: start.x, y: start.y };
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }

  function dragNode(event) {
    const drag = dragRef.current;
    if (!drag) return;
    const dx = (event.clientX - drag.startX) / zoom;
    const dy = (event.clientY - drag.startY) / zoom;
    setPositions((current) => ({
      ...current,
      [drag.tableId]: { x: Math.max(20, drag.x + dx), y: Math.max(20, drag.y + dy) },
    }));
  }

  function endDrag() { dragRef.current = null; }

  async function commitRename(table) {
    const next=editingName.trim();
    if(next && next !== (table.technical_name||table.table_name)) await onRenameTable?.(table,next);
    setEditingTable(null);
  }

  function nodeKeyDown(event, table, source) {
    if(event.key !== "Delete" && event.key !== "Backspace") return;
    if(!(event.ctrlKey||event.metaKey)) return;
    event.preventDefault();
    if(event.shiftKey && source?.mode!=="MANAGED") onDeleteSource?.(source);
    else if(source?.mode==="MANAGED") onDeleteTable?.(table);
  }

  return (
    <section className="visualModelShell">


      <div className="visualModelViewport" ref={viewportRef} tabIndex={0} title="Zoom: Ctrl/Cmd + mouse wheel, +, -, or 0">
        <div className="visualModelCanvas" style={{ width: canvasSize.width * zoom, height: canvasSize.height * zoom }}>
          <div className="visualModelScale" style={{ width: canvasSize.width, height: canvasSize.height, transform: `scale(${zoom})` }}>
            <svg className="modelRelationLayer" width={canvasSize.width} height={canvasSize.height} aria-hidden="true">
              <defs>
                <marker id="relationArrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" />
                </marker>
              </defs>
              {visibleRelations.map((relation) => {
                const sourceTable = tableById[relation.source_table];
                const targetTable = tableById[relation.target_table];
                const source = positions[relation.source_table];
                const target = positions[relation.target_table];
                if (!source || !target || !sourceTable || !targetTable) return null;
                return <path key={relation.id} d={relationPath(source, target, getNodeHeight(sourceTable, compactRelationships), getNodeHeight(targetTable, compactRelationships))} className="modelRelationPath" markerEnd="url(#relationArrow)" />;
              })}
            </svg>

            {visibleTables.map((table) => {
              const source = sourceById[table.data_source];
              const pos = positions[table.id] || { x: 20, y: 20 };
              const selected = selectedId === table.id;
              const fields = table.fields || [];
              return (
                <article
                  className={`modelNode${selected ? " selected" : ""}`}
                  style={{ left: pos.x, top: pos.y }}
                  key={table.id}
                  onClick={() => onSelect(table.id)}
                  onKeyDown={(event)=>nodeKeyDown(event,table,source)}
                  tabIndex={0}
                  title={source?.mode==="MANAGED"?"Ctrl/Cmd+Delete deletes this Platform table":"Ctrl/Cmd+Shift+Delete deletes this connection"}
                >
                  <div className="modelNodeHeader" onPointerDown={(event) => beginDrag(event, table.id)} onPointerMove={dragNode} onPointerUp={endDrag} onPointerCancel={endDrag}>
                    <div className="modelNodeIdentity">
                      <span className={`sourceDot sourceDot-${(source?.mode || "source").toLowerCase()}`} />
                      <div>{editingTable===table.id?<input className="modelNodeRenameInput" autoFocus value={editingName} onPointerDown={e=>e.stopPropagation()} onClick={e=>e.stopPropagation()} onChange={e=>setEditingName(e.target.value)} onKeyDown={e=>{e.stopPropagation();if(e.key==="Enter")commitRename(table);if(e.key==="Escape")setEditingTable(null)}} onBlur={()=>commitRename(table)}/>:<strong onDoubleClick={e=>{e.stopPropagation();setEditingTable(table.id);setEditingName(table.technical_name||table.table_name)}}>{table.technical_name||table.table_name}</strong>}<span>{source?.name || "Source"}</span></div>
                    </div>
                    <span className="modelNodeType">{table.object_type}</span>
                  </div>
                  {!compactRelationships && <div className="modelFieldList">
                    {fields.slice(0, MAX_VISIBLE_FIELDS).map((field) => (
                      <div className="modelFieldRow" key={field.id} title={`${field.name} · ${field.logical_type}`}>
                        <span className="modelFieldKey">{field.is_primary_key ? "PK" : field.is_identity ? "ID" : ""}</span>
                        <span className="modelFieldName">{field.business_name || field.name}{field.business_name && <small>{field.name}</small>}</span>
                        <span className="modelFieldType">{field.logical_type}</span>
                      </div>
                    ))}
                    {fields.length === 0 && <div className="modelNodeEmpty">No fields cataloged</div>}
                    {fields.length > MAX_VISIBLE_FIELDS && <div className="modelMoreFields">+ {fields.length - MAX_VISIBLE_FIELDS} more fields</div>}
                  </div>}
                </article>
              );
            })}

            {visibleTables.length === 0 && <div className="modelCanvasEmpty"><Icon name="model" size={26} /><strong>No matching tables</strong><span>Adjust your search or source filter.</span></div>}
          </div>
        </div>
      </div>
    </section>
  );
}
