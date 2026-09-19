export const EXECUTION_STATUS_LABELS = {
  QUEUED: "En cola",
  RUNNING: "Ejecutando",
  SUCCESS: "Exitosa",
  FAILED: "Fallida",
  CANCELLED: "Cancelada",
  BLOCKED: "Bloqueada",
};

export default function ExecutionStatus({ status }) {
  return <span className={`statusBadge status-${String(status || "").toLowerCase()}`}>{EXECUTION_STATUS_LABELS[status] || status || "—"}</span>;
}
