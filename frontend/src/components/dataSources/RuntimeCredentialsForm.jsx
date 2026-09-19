"use client";

import { useEffect, useState } from "react";

const SSL_MODES = [
  ["disable", "Disable — sin SSL"],
  ["allow", "Allow — usa SSL si el servidor lo exige"],
  ["prefer", "Prefer — prefiere SSL si está disponible"],
  ["require", "Require — exige conexión cifrada"],
  ["verify-ca", "Verify CA — valida la autoridad certificadora"],
  ["verify-full", "Verify Full — valida CA y nombre del servidor"],
];

export default function RuntimeCredentialsForm({ source, value, onChange }) {
  const metadata = source?.connection_metadata || {};
  const [form, setForm] = useState({});

  useEffect(() => {
    const initial = source?.engine === "SQLSERVER"
      ? {
          server: metadata.server || "",
          database: metadata.database || "",
          user: metadata.user || "",
          password: "",
          driver: metadata.driver || "ODBC Driver 18 for SQL Server",
          trusted_connection: Boolean(metadata.trusted_connection),
          encrypt: metadata.encrypt ?? true,
          trust_server_certificate: Boolean(metadata.trust_server_certificate),
          connect_timeout: metadata.connect_timeout || 5,
        }
      : {
          host: metadata.host || "",
          port: metadata.port || 5432,
          database: metadata.database || "",
          user: metadata.user || "",
          password: "",
          sslmode: metadata.sslmode || "prefer",
          connect_timeout: metadata.connect_timeout || 5,
        };
    setForm(initial);
    onChange(initial);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source?.id]);

  function update(event) {
    const { name, value: nextValue, type, checked } = event.target;
    const next = { ...form, [name]: type === "checkbox" ? checked : nextValue };
    setForm(next);
    onChange(next);
  }

  if (!source || !["POSTGRESQL", "SQLSERVER"].includes(source.engine)) return null;

  return (
    <div className="formGrid twoColumns">
      {source.engine === "POSTGRESQL" ? (
        <>
          <label className="field"><span>Host</span><input name="host" value={form.host || ""} onChange={update} /></label>
          <label className="field"><span>Puerto</span><input name="port" type="number" value={form.port || 5432} onChange={update} /></label>
        </>
      ) : (
        <>
          <label className="field"><span>Server</span><input name="server" value={form.server || ""} onChange={update} /></label>
          <label className="field"><span>Driver</span><input name="driver" value={form.driver || ""} onChange={update} /></label>
        </>
      )}
      <label className="field"><span>Database</span><input name="database" value={form.database || ""} onChange={update} /></label>
      {!form.trusted_connection && <label className="field"><span>Usuario</span><input name="user" value={form.user || ""} onChange={update} /></label>}
      {!form.trusted_connection && <label className="field"><span>Contraseña temporal</span><input name="password" type="password" value={form.password || ""} onChange={update} autoComplete="new-password" /></label>}
      <label className="field"><span>Timeout (s)</span><input name="connect_timeout" type="number" min="1" max="60" value={form.connect_timeout || 5} onChange={update} /></label>
      {source.engine === "POSTGRESQL" && <label className="field"><span>SSL mode</span><select name="sslmode" value={form.sslmode || "prefer"} onChange={update}>{SSL_MODES.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>}
      {source.engine === "SQLSERVER" && <div className="checkboxRow fullWidth"><label><input type="checkbox" name="trusted_connection" checked={Boolean(form.trusted_connection)} onChange={update} /> Trusted connection</label><label><input type="checkbox" name="encrypt" checked={Boolean(form.encrypt)} onChange={update} /> Encrypt</label><label><input type="checkbox" name="trust_server_certificate" checked={Boolean(form.trust_server_certificate)} onChange={update} /> Trust server certificate</label></div>}
    </div>
  );
}
