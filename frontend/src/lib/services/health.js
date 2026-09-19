import { publicApi } from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

export async function getLiveness() {
  const response = await publicApi.get(API_ENDPOINTS.health.live);
  return response.data;
}

export async function getReadiness() {
  const response = await publicApi.get(API_ENDPOINTS.health.ready);
  return response.data;
}
