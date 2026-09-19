"use client";

import { useEffect, useState } from "react";

const EMPTY = {
  name: "",
  description: "",
  sql: "SELECT *\nFROM {{asset:UUID}}",
  output_mode: "VIEW",
  refresh_policy: "MANUAL",
  enabled: true,
};

export default function TransformationForm({ workspaceId, initialValue, assets = [], onSubmit, onCancel, isSaving }) {
  const [form, setForm] = useState(EMPTY);

  useEffect(() => {
    setForm(initialValue ? {
      name: initialValue.name || "",
      description: initialValue.description || "",
      sql: initialValue.sql || "",
      output_mode: initialValue.output_mode || "VIEW",
      refresh_policy: initialValue.refresh_policy || "MANUAL",
      enabled: initialValue.enabled !== false,
    } : EMPTY);
  }, [initialValue]);

  function set(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  function insertAsset(asset) {
    const token = `{{asset:${asset.id}}}`;
    set("sql", `${form.sql}${form.sql.endsWith("\n") ? "" : "\n"}${token}`);
  }

  function submit(event) {
    event.preventDefault();
    onSubmit({ workspace: workspaceId, ...form });
  }

  return <form className="formStack" onSubmit={submit}>
    <div className="formGrid twoColumns">
      <label className="field"><span>Nombre</span><input required value={form.name} onChange={(e) => set("name", e.target.value)} /></label>
      <label className="field"><span>Output</span><select value={form.output_mode} onChange={(e) => set("output_mode", e.target.value)}><option value="VIEW">VIEW</option><option value="TABLE">TABLE</option></select></label>
      <label className="field"><span>Refresh policy</span><select value={form.refresh_policy} onChange={(e) => set("refresh_policy", e.target.value)}><option value="MANUAL">MANUAL</option><option value="AUTO">AUTO</option><option value="SCHEDULED">SCHEDULED</option></select></label>
      <label className="checkboxField"><input type="checkbox" checked={form.enabled} onChange={(e) => set("enabled", e.target.checked)} /><span>Transformación habilitada</span></label>
    </div>
    <label className="field"><span>Descripción</span><textarea rows="2" value={form.description} onChange={(e) => set("description", e.target.value)} /></label>
    <div className="field"><span>Assets MANAGED disponibles</span><div className="chipList">{assets.length ? assets.map((asset) => <button type="button" className="chipButton" key={asset.id} onClick={() => insertAsset(asset)} title={`Insertar {{asset:${asset.id}}}`}>{asset.name}</button>) : <small>No hay assets tabulares MANAGED.</small>}</div></div>
    <label className="field"><span>SQL — solo SELECT/WITH</span><textarea className="codeArea" rows="12" required value={form.sql} onChange={(e) => set("sql", e.target.value)} /><small>Referencia assets con <code>{"{{asset:UUID}}"}</code>. No uses nombres físicos ni credenciales.</small></label>
    <div className="formActions"><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button><button type="submit" className="button primaryButton" disabled={isSaving}>{isSaving ? "Guardando..." : "Guardar"}</button></div>
  </form>;
}
