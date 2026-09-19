"use client";
import { useEffect, useState } from "react";

export default function SemanticModelForm({ workspaceId, tables, initialValue, onSubmit, onCancel, isSaving }) {
  const [form, setForm] = useState({ name: "", description: "", base_table: "", enabled: true });
  useEffect(() => {
    setForm({
      name: initialValue?.name || "",
      description: initialValue?.description || "",
      base_table: initialValue?.base_table || tables?.[0]?.id || "",
      enabled: initialValue?.enabled ?? true,
    });
  }, [initialValue, tables]);
  function set(name, value) { setForm((old) => ({ ...old, [name]: value })); }
  function submit(e) { e.preventDefault(); onSubmit({ workspace: workspaceId, ...form }); }
  return <form className="formGrid" onSubmit={submit}>
    <label className="fieldGroup"><span>Nombre</span><input value={form.name} onChange={(e)=>set("name",e.target.value)} required /></label>
    <label className="fieldGroup"><span>Tabla base MANAGED</span><select value={form.base_table} onChange={(e)=>set("base_table",e.target.value)} required><option value="">Seleccionar</option>{tables.map(t=><option key={t.id} value={t.id}>{t.technical_name||t.table_name}</option>)}</select></label>
    <label className="fieldGroup fullWidth"><span>Descripción</span><textarea rows="3" value={form.description} onChange={(e)=>set("description",e.target.value)} /></label>
    <label className="checkField"><input type="checkbox" checked={form.enabled} onChange={(e)=>set("enabled",e.target.checked)} /> Habilitado</label>
    <div className="formActions fullWidth"><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button><button type="submit" className="button primaryButton" disabled={isSaving}>{isSaving ? "Guardando..." : "Guardar"}</button></div>
  </form>;
}
