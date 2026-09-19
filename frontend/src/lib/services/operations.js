import api from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

export async function getOperationalStatus() {
  const response = await api.get(API_ENDPOINTS.operations.status);
  return response.data;
}
