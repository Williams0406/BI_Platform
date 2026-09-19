"use client";

import { useState } from "react";

const ACTIONS = ["UPDATE_FIELD", "MOVE_KANBAN", "EDIT_CELL", "RESIZE_CALENDAR", "SUBMIT_FORM"];

export default function ActionRuleForm({ onSubmit, onCancel, isSaving }) {
  const [form, setForm] = useState({ name: "", action_type: "UPDATE_FIELD", enabled: true, config: "{}" });
  const [error, setError] = useState("");
  function submit(event) {
    event.preventDefault(); setError("");
    try { onSubmit({ name: form.name.trim(), action_type: form.action_type, enabled: form.enabled, config: JSON.parse(form.config || "{}") }); }
    catch { setError("Config debe ser un objeto JSON válido."); }
  }
  return <form className="formStack" onSubmit={submit}>
    {error && <div className="inlineError">{error}</div>}
    <div className="formGrid threeColumns"><label>Nombre<input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label><label>Acción<select value={form.action_type} onChange={(e) => setForm({ ...form, action_type: e.target.value })}>{ACTIONS.map((action) => <option key={action}>{action}</option>)}</select></label><label className="checkboxLabel"><input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} /> Habilitada</label></div>
    <label>Config JSON<textarea rows="4" value={form.config} onChange={(e) => setForm({ ...form, config: e.target.value })} /></label>
    <div className="formActions"><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button><button type="submit" className="button primaryButton" disabled={isSaving}>{isSaving ? "Guardando..." : "Agregar regla"}</button></div>
  </form>;
}
