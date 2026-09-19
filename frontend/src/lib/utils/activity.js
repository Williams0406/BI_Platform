export function normalizeCollection(value) {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.results)) return value.results;
  return [];
}

export function executionLabel(item) {
  const type = String(item?.object_type || "Execution").replaceAll("_", " ").toLowerCase();
  return type.replace(/\b\w/g, (m) => m.toUpperCase());
}

export function executionTimestamp(item) {
  return item?.finished_at || item?.started_at || item?.queued_at || null;
}

export function formatRelativeTime(value) {
  if (!value) return "—";
  const diff = Date.now() - new Date(value).getTime();
  if (!Number.isFinite(diff)) return "—";
  const min = Math.max(0, Math.round(diff / 60000));
  if (min < 1) return "ahora";
  if (min < 60) return `hace ${min} min`;
  const hours = Math.round(min / 60);
  if (hours < 24) return `hace ${hours} h`;
  const days = Math.round(hours / 24);
  return `hace ${days} d`;
}
