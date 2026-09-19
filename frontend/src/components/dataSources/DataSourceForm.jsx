"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { listBindings, listGateways } from "@/lib/services/customerGateway";
import { getApiErrorMessage } from "@/lib/utils/errors";

const MODES = [
  {
    value: "MANAGED",
    label: "Managed / Plataforma",
    description: "Datos administrados y almacenados por la plataforma. No requiere parámetros de red.",
  },
  {
    value: "EXTERNAL",
    label: "External",
    description: "Base de datos accesible directamente desde el backend de la plataforma.",
  },
  {
    value: "PRIVATE_GATEWAY",
    label: "Private Gateway",
    description: "Base privada u on-premise accesible mediante un Gateway instalado en la red del cliente.",
  },
];

const ENGINES = [
  { value: "PLATFORM_POSTGRES", label: "PostgreSQL administrado" },
  { value: "POSTGRESQL", label: "PostgreSQL" },
  { value: "SQLSERVER", label: "Microsoft SQL Server" },
  { value: "OTHER", label: "Otro" },
];

const STATUSES = [
  { value: "DRAFT", label: "Draft", description: "Configuración todavía en preparación; no debería usarse operacionalmente." },
  { value: "ACTIVE", label: "Active", description: "Fuente habilitada y lista para utilizarse." },
  { value: "UNAVAILABLE", label: "Unavailable", description: "La fuente debería estar disponible, pero actualmente no puede utilizarse." },
  { value: "ARCHIVED", label: "Archived", description: "Fuente retirada del uso activo, conservada por historial y auditoría." },
];

const SSL_MODES = [
  { value: "disable", label: "Disable — sin SSL" },
  { value: "allow", label: "Allow — usa SSL si el servidor lo exige" },
  { value: "prefer", label: "Prefer — prefiere SSL si está disponible" },
  { value: "require", label: "Require — exige conexión cifrada" },
  { value: "verify-ca", label: "Verify CA — exige SSL y valida la autoridad certificadora" },
  { value: "verify-full", label: "Verify Full — valida CA y nombre del servidor" },
];

function listValue(value) {
  if (Array.isArray(value)) return value;
  return value?.results || [];
}

function metadataFromSource(source) {
  return {
    host: source?.connection_metadata?.host || "",
    port: source?.connection_metadata?.port || "",
    database: source?.connection_metadata?.database || "",
    user: source?.connection_metadata?.user || "",
    sslmode: source?.connection_metadata?.sslmode || "prefer",
    server: source?.connection_metadata?.server || "",
    driver: source?.connection_metadata?.driver || "ODBC Driver 18 for SQL Server",
    trusted_connection: Boolean(source?.connection_metadata?.trusted_connection),
    encrypt: source?.connection_metadata?.encrypt ?? true,
    trust_server_certificate: Boolean(source?.connection_metadata?.trust_server_certificate),
    connect_timeout: source?.connection_metadata?.connect_timeout || 5,
  };
}

function CapabilityOption({ name, checked, onChange, disabled, label, description, tone = "default" }) {
  return (
    <label className={`dataSourceCapability ${checked ? "selected" : ""} ${tone === "danger" ? "danger" : ""} ${disabled ? "disabled" : ""}`}>
      <input type="checkbox" name={name} checked={checked} onChange={onChange} disabled={disabled} />
      <span className="dataSourceCapabilityBody">
        <strong>{label}</strong>
        <small>{description}</small>
      </span>
    </label>
  );
}

export default function DataSourceForm({ source, workspaceId, onSubmit, onCancel, isSaving }) {
  const [form, setForm] = useState({
    name: "",
    mode: "EXTERNAL",
    engine: "POSTGRESQL",
    status: "DRAFT",
    can_read: true,
    can_write: false,
    can_ddl: false,
    metadata: metadataFromSource(null),
  });
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [gateways, setGateways] = useState([]);
  const [gatewayBinding, setGatewayBinding] = useState({ gateway: "", local_connection_name: "" });
  const [gatewayLoading, setGatewayLoading] = useState(false);
  const [gatewayError, setGatewayError] = useState("");

  useEffect(() => {
    if (!source) return;
    setForm({
      name: source.name || "",
      mode: source.mode || "EXTERNAL",
      engine: source.engine || "POSTGRESQL",
      status: source.status || "DRAFT",
      can_read: Boolean(source.can_read),
      can_write: Boolean(source.can_write),
      can_ddl: Boolean(source.can_ddl),
      metadata: metadataFromSource(source),
    });
  }, [source]);

  const isManaged = form.mode === "MANAGED";
  const isPrivateGateway = form.mode === "PRIVATE_GATEWAY";
  const isExternal = form.mode === "EXTERNAL";
  const isPostgres = form.engine === "POSTGRESQL";
  const isSqlServer = form.engine === "SQLSERVER";

  useEffect(() => {
    if (!isPrivateGateway || !workspaceId) return;
    let cancelled = false;
    (async () => {
      setGatewayLoading(true);
      setGatewayError("");
      try {
        const [gatewayResponse, bindingResponse] = await Promise.all([
          listGateways(workspaceId),
          listBindings(),
        ]);
        if (cancelled) return;
        const workspaceGateways = listValue(gatewayResponse);
        setGateways(workspaceGateways);
        const currentBinding = source?.id
          ? listValue(bindingResponse).find((item) => item.data_source === source.id)
          : null;
        setGatewayBinding({
          gateway: currentBinding?.gateway || "",
          local_connection_name: currentBinding?.local_connection_name || "",
        });
      } catch (error) {
        if (!cancelled) setGatewayError(getApiErrorMessage(error));
      } finally {
        if (!cancelled) setGatewayLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [isPrivateGateway, source?.id, workspaceId]);

  const availableEngines = useMemo(() => {
    if (isManaged) return ENGINES.filter((item) => item.value === "PLATFORM_POSTGRES");
    return ENGINES.filter((item) => item.value !== "PLATFORM_POSTGRES");
  }, [isManaged]);

  const selectedStatus = STATUSES.find((item) => item.value === form.status);
  const selectedMode = MODES.find((item) => item.value === form.mode);

  function updateField(event) {
    const { name, value, type, checked } = event.target;
    setForm((current) => ({ ...current, [name]: type === "checkbox" ? checked : value }));
  }

  function updateMetadata(event) {
    const { name, value, type, checked } = event.target;
    setForm((current) => ({
      ...current,
      metadata: {
        ...current.metadata,
        [name]: type === "checkbox" ? checked : value,
      },
    }));
  }

  function handleModeChange(mode) {
    setAdvancedOpen(false);
    setForm((current) => ({
      ...current,
      mode,
      engine: mode === "MANAGED" ? "PLATFORM_POSTGRES" : current.engine === "PLATFORM_POSTGRES" ? "POSTGRESQL" : current.engine,
      can_read: true,
      can_write: mode === "MANAGED" ? true : false,
      can_ddl: mode === "MANAGED" ? true : false,
    }));
  }

  function buildMetadata() {
    if (isManaged || isPrivateGateway) return {};
    if (isPostgres) {
      const output = {
        host: form.metadata.host.trim(),
        database: form.metadata.database.trim(),
        user: form.metadata.user.trim(),
        sslmode: form.metadata.sslmode || "prefer",
        connect_timeout: Number(form.metadata.connect_timeout || 5),
      };
      if (form.metadata.port) output.port = Number(form.metadata.port);
      return output;
    }
    if (isSqlServer) {
      return {
        server: form.metadata.server.trim(),
        database: form.metadata.database.trim(),
        user: form.metadata.user.trim(),
        driver: form.metadata.driver || "ODBC Driver 18 for SQL Server",
        trusted_connection: Boolean(form.metadata.trusted_connection),
        encrypt: Boolean(form.metadata.encrypt),
        trust_server_certificate: Boolean(form.metadata.trust_server_certificate),
        connect_timeout: Number(form.metadata.connect_timeout || 5),
      };
    }
    return {};
  }

  function submit(event) {
    event.preventDefault();
    const dataSourcePayload = {
      workspace: workspaceId,
      name: form.name.trim(),
      mode: form.mode,
      engine: form.engine,
      status: form.status,
      can_read: isManaged ? true : form.can_read,
      can_write: isManaged ? true : form.can_write,
      can_ddl: isManaged ? true : form.can_ddl,
      connection_metadata: buildMetadata(),
    };

    onSubmit({
      data_source: dataSourcePayload,
      gateway_binding: isPrivateGateway
        ? {
            gateway: gatewayBinding.gateway,
            local_connection_name: gatewayBinding.local_connection_name.trim(),
          }
        : null,
    });
  }

  return (
    <form className="inlineForm dataSourceConnectForm" onSubmit={submit}>
      <section className="dataSourceFormSection dataSourceIdentitySection">
        <div className="dataSourceSectionHeading">
          <div>
            <span className="dataSourceStep">1</span>
            <div><h3>Fuente</h3></div>
          </div>
        </div>

        <label className="field dataSourceNameField">
          <span>Nombre</span>
          <input name="name" required value={form.name} onChange={updateField} placeholder="Ej. ERP Producción" autoFocus />
          
        </label>

        <div className="dataSourceModeGroup" role="radiogroup" aria-label="Modo de la fuente">
          {MODES.map((item) => (
            <button
              type="button"
              key={item.value}
              className={`dataSourceModeCard ${form.mode === item.value ? "selected" : ""}`}
              onClick={() => handleModeChange(item.value)}
              aria-pressed={form.mode === item.value}
            >
              <span className="dataSourceModeRadio" aria-hidden="true" />
              <strong>{item.label}</strong>
              <small>{item.description}</small>
            </button>
          ))}
        </div>
        <p className="dataSourceModeSummary"><strong>{selectedMode?.label}:</strong> {selectedMode?.description}</p>
      </section>

      <section className="dataSourceFormSection">
        <div className="dataSourceSectionHeading">
          <div>
            <span className="dataSourceStep">2</span>
            <div><h3>Configuración</h3><p>La información solicitada cambia según el modo seleccionado.</p></div>
          </div>
        </div>

        <div className="formGrid twoColumns dataSourceCoreGrid">
          <label className="field">
            <span>Motor</span>
            <select name="engine" value={form.engine} onChange={updateField} disabled={isManaged}>
              {availableEngines.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
            <small>{isManaged ? "Administrado automáticamente por la plataforma." : "Motor de la base de datos de origen."}</small>
          </label>

          <label className="field">
            <span>Estado</span>
            <select name="status" value={form.status} onChange={updateField}>
              {STATUSES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
            <small>{selectedStatus?.description}</small>
          </label>
        </div>

        {isManaged && (
          <div className="dataSourceManagedPanel">
            <div className="dataSourceManagedIcon">P</div>
            <div>
              <strong>Infraestructura administrada por la plataforma</strong>
              <p>No necesitas Host, Puerto, Database, Usuario ni SSL. La plataforma administra internamente el almacenamiento y la conexión.</p>
            </div>
          </div>
        )}

        {isExternal && (isPostgres || isSqlServer) && (
          <div className="dataSourceConnectionPanel">
            <div className="dataSourcePanelHeader">
              <div><h4>Conexión</h4><p>Parámetros no sensibles necesarios para localizar la base de datos.</p></div>
              <span className="dataSourceSecurityBadge">No guarda contraseñas</span>
            </div>
            <div className="formGrid twoColumns">
              {isPostgres ? (
                <label className="field"><span>Host</span><input name="host" required value={form.metadata.host} onChange={updateMetadata} placeholder="db.empresa.com" /></label>
              ) : (
                <label className="field"><span>Server</span><input name="server" required value={form.metadata.server} onChange={updateMetadata} placeholder="SERVIDOR\\INSTANCIA" /></label>
              )}
              <label className="field"><span>Database</span><input name="database" required value={form.metadata.database} onChange={updateMetadata} placeholder="analytics" /></label>
              {!form.metadata.trusted_connection && (
                <label className="field">
                  <span>Usuario de la base de datos</span>
                  <input name="user" value={form.metadata.user} onChange={updateMetadata} placeholder="bi_reader" autoComplete="off" />
                  <small>Es el usuario del motor de base de datos, no tu usuario de la plataforma.</small>
                </label>
              )}
              {isPostgres && (
                <label className="field"><span>Puerto</span><input name="port" type="number" min="1" max="65535" value={form.metadata.port} onChange={updateMetadata} placeholder="5432" /></label>
              )}
            </div>

            <button type="button" className="dataSourceAdvancedToggle" onClick={() => setAdvancedOpen((value) => !value)} aria-expanded={advancedOpen}>
              <span>Advanced settings</span><span aria-hidden="true">{advancedOpen ? "−" : "+"}</span>
            </button>

            {advancedOpen && (
              <div className="dataSourceAdvancedPanel">
                {isPostgres && (
                  <label className="field">
                    <span>SSL mode</span>
                    <select name="sslmode" value={form.metadata.sslmode} onChange={updateMetadata}>
                      {SSL_MODES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                    </select>
                    <small>Para producción, usa Require o un nivel de verificación superior cuando el servidor lo soporte.</small>
                  </label>
                )}
                {isSqlServer && (
                  <label className="field"><span>ODBC driver</span><input name="driver" value={form.metadata.driver} onChange={updateMetadata} /></label>
                )}
                <label className="field">
                  <span>Timeout (s)</span>
                  <input name="connect_timeout" type="number" min="1" max="60" value={form.metadata.connect_timeout} onChange={updateMetadata} />
                  <small>Tiempo máximo para establecer la conexión antes de cancelarla.</small>
                </label>
                {isSqlServer && (
                  <div className="dataSourceSqlSecurity">
                    <label><input type="checkbox" name="trusted_connection" checked={form.metadata.trusted_connection} onChange={updateMetadata} /> Trusted connection</label>
                    <label><input type="checkbox" name="encrypt" checked={form.metadata.encrypt} onChange={updateMetadata} /> Encrypt</label>
                    <label><input type="checkbox" name="trust_server_certificate" checked={form.metadata.trust_server_certificate} onChange={updateMetadata} /> Trust server certificate</label>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {isExternal && !isPostgres && !isSqlServer && (
          <div className="dataSourceManagedPanel neutral">
            <div className="dataSourceManagedIcon">i</div>
            <div><strong>Motor personalizado</strong><p>Este motor todavía no tiene un formulario de conexión directo. Puedes registrar la definición y ampliar posteriormente su Connector.</p></div>
          </div>
        )}

        {isPrivateGateway && (
          <div className="dataSourceConnectionPanel privateGatewayPanel">
            <div className="dataSourcePanelHeader">
              <div><h4>Private Gateway</h4><p>Selecciona el agente que puede alcanzar la base privada y la conexión local configurada en ese agente.</p></div>
              <span className="dataSourceSecurityBadge">Credenciales permanecen on-premise</span>
            </div>

            {gatewayError && <div className="dataSourceInlineError">{gatewayError}</div>}
            <div className="formGrid twoColumns">
              <label className="field">
                <span>Gateway agent</span>
                <select value={gatewayBinding.gateway} onChange={(event) => setGatewayBinding((current) => ({ ...current, gateway: event.target.value }))} disabled={gatewayLoading}>
                  <option value="">{gatewayLoading ? "Cargando gateways..." : "Seleccionar gateway"}</option>
                  {gateways.map((gateway) => (
                    <option key={gateway.id} value={gateway.id}>{gateway.name} · {gateway.effective_status || gateway.status}</option>
                  ))}
                </select>
                <small>El agente debe estar registrado en este workspace.</small>
              </label>
              <label className="field">
                <span>Nombre de conexión local</span>
                <input value={gatewayBinding.local_connection_name} onChange={(event) => setGatewayBinding((current) => ({ ...current, local_connection_name: event.target.value }))} placeholder="erp_production" />
                <small>Debe coincidir con el nombre definido en la configuración local del Gateway.</small>
              </label>
            </div>

            {!gatewayLoading && gateways.length === 0 && (
              <div className="dataSourceGatewayEmpty">
                <span>No hay Gateway agents registrados. Puedes guardar la fuente como Draft y completar el enlace después.</span>
                <Link href="/app/customer-gateway">Configurar Private Gateway →</Link>
              </div>
            )}

            <div className="dataSourceGatewayFlow">
              <span>BI Platform</span><span>→</span><span>Gateway</span><span>→</span><span>Base privada</span>
            </div>
            <p className="dataSourcePrivateNote">Host, puerto, usuario, contraseña y SSL de la base privada se configuran en el host del Gateway. No se envían ni persisten en esta pantalla.</p>
          </div>
        )}
      </section>

      <section className="dataSourceFormSection">
        <div className="dataSourceSectionHeading">
          <div>
            <span className="dataSourceStep">3</span>
            <div><h3>Capacidades</h3><p>Aplica principio de mínimo privilegio: habilita solo lo que esta fuente necesita.</p></div>
          </div>
        </div>
        <div className="dataSourceCapabilitiesGrid">
          <CapabilityOption name="can_read" checked={isManaged ? true : form.can_read} onChange={updateField} disabled={isManaged} label="READ" description="Consultar, explorar y analizar datos." />
          <CapabilityOption name="can_write" checked={isManaged ? true : form.can_write} onChange={updateField} disabled={isManaged} label="WRITE" description="Insertar, actualizar o eliminar registros." />
          <CapabilityOption name="can_ddl" checked={isManaged ? true : form.can_ddl} onChange={updateField} disabled={isManaged} label="DDL" description="Crear o modificar estructuras de base de datos." tone="danger" />
        </div>
        {isManaged && <p className="dataSourceManagedCapabilityNote">Managed / Plataforma requiere READ, WRITE y DDL para administrar sus propias tablas internas.</p>}
      </section>

      <div className="formActions dataSourceFormActions">
        <button type="button" className="button secondaryButton" onClick={onCancel}>Cancelar</button>
        <button type="submit" className="button primaryButton" disabled={isSaving || (isPrivateGateway && form.status === "ACTIVE" && (!gatewayBinding.gateway || !gatewayBinding.local_connection_name.trim()))}>
          {isSaving ? "Guardando..." : source ? "Guardar cambios" : "Connect data"}
        </button>
      </div>
    </form>
  );
}
