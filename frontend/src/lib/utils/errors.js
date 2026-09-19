function firstValue(value) {
  if (Array.isArray(value)) {
    return value.length ? firstValue(value[0]) : null;
  }

  if (value && typeof value === "object") {
    for (const nested of Object.values(value)) {
      const result = firstValue(nested);
      if (result) return result;
    }
    return null;
  }

  if (typeof value === "string") {
    return value;
  }

  return null;
}

export function getApiErrorMessage(error, fallback = "No se pudo completar la operación.") {
  if (!error) return fallback;

  if (error.code === "ECONNABORTED") {
    return "La solicitud tardó demasiado. Verifica que el backend esté disponible.";
  }

  if (!error.response) {
    return "No se pudo conectar con el backend. Verifica que Django esté ejecutándose.";
  }

  const data = error.response?.data;

  if (typeof data === "string" && data.trim()) {
    return data;
  }

  if (data?.detail) {
    return String(data.detail);
  }

  const nestedMessage = firstValue(data);
  return nestedMessage || fallback;
}
