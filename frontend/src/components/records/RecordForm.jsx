"use client";

import { useEffect, useState } from "react";

function initialValue(field, record) {
  if (record && Object.prototype.hasOwnProperty.call(record, field.name)) {
    const value = record[field.name];
    if (field.logical_type === "JSON" && value !== null && typeof value === "object") return JSON.stringify(value, null, 2);
    if (["DATETIME", "DATETIME_TZ"].includes(field.logical_type) && typeof value === "string") return value.slice(0, 16);
    return value ?? "";
  }
  return "";
}

function normalizeValue(field, raw) {
  if (raw === "" && field.nullable) return null;
  if (field.logical_type === "BOOLEAN") return raw === true || raw === "true";
  if (["INTEGER", "BIGINT"].includes(field.logical_type)) return raw === "" ? null : Number.parseInt(raw, 10);
  if (["FLOAT", "DECIMAL"].includes(field.logical_type)) return raw === "" ? null : Number(raw);
  if (field.logical_type === "JSON") {
    if (raw === "") return field.nullable ? null : {};
    return JSON.parse(raw);
  }
  return raw;
}

function inputType(field) {
  if (["INTEGER", "BIGINT", "FLOAT", "DECIMAL"].includes(field.logical_type)) return "number";
  if (field.logical_type === "DATE") return "date";
  if (["DATETIME", "DATETIME_TZ"].includes(field.logical_type)) return "datetime-local";
  if (field.logical_type === "TIME") return "time";
  return "text";
}

export default function RecordForm({ table, record = null, onSubmit, onCancel, isSaving }) {
  const [values, setValues] = useState({});
  const [localError, setLocalError] = useState("");

  useEffect(() => {
    const next = {};
    for (const field of table.fields || []) next[field.name] = initialValue(field, record);
    setValues(next);
  }, [table, record]);

  async function submit(event) {
    event.preventDefault();
    setLocalError("");
    try {
      const payload = {};
      for (const field of table.fields || []) {
        if (record && field.is_primary_key) continue;
        if (!record && field.is_identity && values[field.name] === "") continue;
        if (!record && values[field.name] === "" && field.default_value) continue;
        payload[field.name] = normalizeValue(field, values[field.name]);
      }
      await onSubmit(payload);
    } catch (error) {
      setLocalError(error instanceof SyntaxError ? "El campo JSON no contiene JSON válido." : error.message);
    }
  }

  return <form className="formGrid" onSubmit={submit}>
    {localError && <div className="alert alert-error">{localError}</div>}
    <div className="recordFormGrid">{(table.fields || []).map((field) => {
      const disabled = Boolean(record && field.is_primary_key) || (!record && field.is_identity);
      if (field.logical_type === "BOOLEAN") return <label className="field checkboxRecordField" key={field.id}><span>{field.name}{field.is_primary_key ? " · PK" : ""}</span><select value={String(values[field.name] ?? "")} disabled={disabled} onChange={(e) => setValues((current) => ({ ...current, [field.name]: e.target.value }))}><option value="">{field.nullable ? "NULL" : "Seleccionar"}</option><option value="true">true</option><option value="false">false</option></select></label>;
      if (["TEXT", "JSON"].includes(field.logical_type)) return <label className="field fullWidth" key={field.id}><span>{field.name} · {field.logical_type}{field.is_primary_key ? " · PK" : ""}</span><textarea rows={field.logical_type === "JSON" ? 6 : 4} value={values[field.name] ?? ""} disabled={disabled} onChange={(e) => setValues((current) => ({ ...current, [field.name]: e.target.value }))} required={!field.nullable && !field.default_value && !field.is_identity} /></label>;
      return <label className="field" key={field.id}><span>{field.name} · {field.logical_type}{field.is_primary_key ? " · PK" : ""}{field.is_identity ? " · Identity" : ""}</span><input type={inputType(field)} step={["FLOAT", "DECIMAL"].includes(field.logical_type) ? "any" : undefined} value={values[field.name] ?? ""} disabled={disabled} onChange={(e) => setValues((current) => ({ ...current, [field.name]: e.target.value }))} required={!field.nullable && !field.default_value && !field.is_identity} /></label>;
    })}</div>
    <div className="formActions"><button type="submit" className="button primaryButton" disabled={isSaving}>{isSaving ? "Guardando..." : record ? "Guardar cambios" : "Crear registro"}</button><button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button></div>
  </form>;
}
