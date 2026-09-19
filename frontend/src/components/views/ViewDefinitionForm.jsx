"use client";

import { useEffect, useMemo, useState } from "react";

export const VIEW_TYPES = ["TABLE", "SPREADSHEET", "KANBAN", "MATRIX", "FORM", "CALENDAR"];

export default function ViewDefinitionForm({ workspaceId, tables, initialValue, onSubmit, onCancel, isSaving }) {
  const [form, setForm] = useState({
    name: "",
    source_table: "",
    view_type: "TABLE",
    status: "ACTIVE",
    config: "{}",
    default_filters: "[]",
    default_ordering: "[]",
  });
  const [localError, setLocalError] = useState("");

  useEffect(() => {
    if (!initialValue) return;
    setForm({
      name: initialValue.name || "",
      source_table: initialValue.source_table || "",
      view_type: initialValue.view_type || "TABLE",
      status: initialValue.status || "ACTIVE",
      config: JSON.stringify(initialValue.config || {}, null, 2),
      default_filters: JSON.stringify(initialValue.default_filters || [], null, 2),
      default_ordering: JSON.stringify(initialValue.default_ordering || [], null, 2),
    });
  }, [initialValue]);

  const selectedTable = useMemo(() => tables.find((item) => item.id === form.source_table), [tables, form.source_table]);

  function set(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  function submit(event) {
    event.preventDefault();
    setLocalError("");
    try {
      const config = JSON.parse(form.config || "{}");
      const defaultFilters = JSON.parse(form.default_filters || "[]");
      const defaultOrdering = JSON.parse(form.default_ordering || "[]");
      if (!Array.isArray(defaultFilters) || !Array.isArray(defaultOrdering)) throw new Error("Filtros y orden deben ser listas JSON.");
      onSubmit({
        workspace: workspaceId,
        source_table: form.source_table,
        name: form.name.trim(),
        view_type: form.view_type,
        status: form.status,
        config,
        default_filters: defaultFilters,
        default_ordering: defaultOrdering,
      });
    } catch (error) {
      setLocalError(error.message || "JSON inválido.");
    }
  }

  return <form className="formStack" onSubmit={submit}>
    {localError && <div className="inlineError">{localError}</div>}
    <div className="formGrid twoColumns">
      <label>Nombre<input required value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Pedidos operativos" /></label>
      <label>Tipo<select value={form.view_type} onChange={(e) => set("view_type", e.target.value)}>{VIEW_TYPES.map((type) => <option key={type}>{type}</option>)}</select></label>
      <label>Tabla fuente<select required disabled={Boolean(initialValue)} value={form.source_table} onChange={(e) => set("source_table", e.target.value)}><option value="">Seleccionar tabla MANAGED</option>{tables.map((table) => <option key={table.id} value={table.id}>{table.technical_name||table.table_name}</option>)}</select></label>
      <label>Estado<select value={form.status} onChange={(e) => set("status", e.target.value)}><option value="ACTIVE">ACTIVE</option><option value="ARCHIVED">ARCHIVED</option></select></label>
    </div>
    {selectedTable && <p className="helperText">Fuente: {selectedTable.technical_name||selectedTable.table_name} · {(selectedTable.fields || []).length} campos</p>}
    <div className="formGrid threeColumns">
      <label>Config JSON<textarea rows="7" value={form.config} onChange={(e) => set("config", e.target.value)} /></label>
      <label>Filtros predeterminados<textarea rows="7" value={form.default_filters} onChange={(e) => set("default_filters", e.target.value)} placeholder='[{"field":"status","operator":"eq","value":"OPEN"}]' /></label>
      <label>Orden predeterminado<textarea rows="7" value={form.default_ordering} onChange={(e) => set("default_ordering", e.target.value)} placeholder='["-created_at"]' /></label>
    </div>
    <div className="formActions"><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button><button type="submit" className="button primaryButton" disabled={isSaving}>{isSaving ? "Guardando..." : initialValue ? "Guardar cambios" : "Crear vista"}</button></div>
  </form>;
}
