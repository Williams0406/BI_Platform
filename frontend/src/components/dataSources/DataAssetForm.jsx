"use client";

import { useEffect, useState } from "react";

const TYPES = ["TABLE", "VIEW", "DERIVED_TABLE", "DATASET", "METRIC", "CHART", "DASHBOARD", "REPORT", "ML_MODEL", "OPTIMIZATION_MODEL", "OTHER"];
const STATUSES = ["ACTIVE", "STALE", "ARCHIVED"];

export default function DataAssetForm({ asset, workspaceId, sources, onSubmit, onCancel, isSaving }) {
  const [form, setForm] = useState({ data_source: "", name: "", asset_type: "TABLE", status: "ACTIVE", physical_schema: "", physical_name: "" });

  useEffect(() => {
    if (!asset) return;
    setForm({
      data_source: asset.data_source || "",
      name: asset.name || "",
      asset_type: asset.asset_type || "TABLE",
      status: asset.status || "ACTIVE",
      physical_schema: asset.physical_schema || "",
      physical_name: asset.physical_name || "",
    });
  }, [asset]);

  function update(event) { setForm((current) => ({ ...current, [event.target.name]: event.target.value })); }
  function submit(event) {
    event.preventDefault();
    onSubmit({
      workspace: workspaceId,
      data_source: form.data_source || null,
      name: form.name.trim(),
      asset_type: form.asset_type,
      status: form.status,
      physical_schema: form.physical_schema.trim(),
      physical_name: form.physical_name.trim(),
      metadata: asset?.metadata || {},
    });
  }

  return <form className="inlineForm" onSubmit={submit}><div className="formGrid twoColumns">
    <label className="field"><span>Nombre lógico</span><input name="name" required value={form.name} onChange={update} /></label>
    <label className="field"><span>Data Source</span><select name="data_source" value={form.data_source} onChange={update}><option value="">Sin fuente</option>{sources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}</select></label>
    <label className="field"><span>Tipo</span><select name="asset_type" value={form.asset_type} onChange={update}>{TYPES.map((item) => <option key={item}>{item}</option>)}</select></label>
    <label className="field"><span>Estado</span><select name="status" value={form.status} onChange={update}>{STATUSES.map((item) => <option key={item}>{item}</option>)}</select></label>
    <label className="field"><span>Schema físico</span><input name="physical_schema" value={form.physical_schema} onChange={update} /></label>
    <label className="field"><span>Nombre físico</span><input name="physical_name" value={form.physical_name} onChange={update} /></label>
  </div><div className="formActions"><button type="submit" className="button primaryButton" disabled={isSaving}>{isSaving ? "Guardando..." : asset ? "Guardar cambios" : "Crear Data Asset"}</button><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button></div></form>;
}
