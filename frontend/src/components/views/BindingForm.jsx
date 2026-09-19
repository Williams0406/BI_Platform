"use client";

import { useMemo, useState } from "react";

const ROLES = ["DISPLAY", "TITLE", "SUBTITLE", "STATUS", "GROUP", "ROW", "COLUMN", "VALUE", "START_DATE", "END_DATE", "LABEL", "COLOR", "SORT", "HIDDEN"];

export default function BindingForm({ fields, bindings, onSubmit, onCancel, isSaving }) {
  const available = useMemo(() => fields || [], [fields]);
  const [form, setForm] = useState({ field: available[0]?.id || "", role: "DISPLAY", alias: "", editable: false, required: false, position: bindings?.length || 0, options: "{}" });
  const [error, setError] = useState("");
  function set(name, value) { setForm((current) => ({ ...current, [name]: value })); }
  function submit(event) {
    event.preventDefault(); setError("");
    try {
      onSubmit({ ...form, position: Number(form.position || 0), options: JSON.parse(form.options || "{}") });
    } catch { setError("Options debe ser un objeto JSON válido."); }
  }
  return <form className="formStack" onSubmit={submit}>
    {error && <div className="inlineError">{error}</div>}
    <div className="formGrid threeColumns">
      <label>Campo<select required value={form.field} onChange={(e) => set("field", e.target.value)}><option value="">Seleccionar</option>{available.map((field) => <option value={field.id} key={field.id}>{field.name} · {field.logical_type}</option>)}</select></label>
      <label>Rol<select value={form.role} onChange={(e) => set("role", e.target.value)}>{ROLES.map((role) => <option key={role}>{role}</option>)}</select></label>
      <label>Alias<input value={form.alias} onChange={(e) => set("alias", e.target.value)} /></label>
      <label>Posición<input type="number" min="0" value={form.position} onChange={(e) => set("position", e.target.value)} /></label>
      <label className="checkboxLabel"><input type="checkbox" checked={form.editable} onChange={(e) => set("editable", e.target.checked)} /> Editable</label>
      <label className="checkboxLabel"><input type="checkbox" checked={form.required} onChange={(e) => set("required", e.target.checked)} /> Requerido</label>
    </div>
    <label>Options JSON<textarea rows="4" value={form.options} onChange={(e) => set("options", e.target.value)} placeholder='{"choices":["OPEN","DONE"]}' /></label>
    <div className="formActions"><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button><button type="submit" className="button primaryButton" disabled={isSaving}>{isSaving ? "Guardando..." : "Agregar binding"}</button></div>
  </form>;
}
