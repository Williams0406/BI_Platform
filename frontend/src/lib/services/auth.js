import api, { publicApi } from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";
import { clearTokens, saveTokens } from "@/lib/auth/tokens";

export async function loginRequest({ email, password }) {
  const response = await publicApi.post(API_ENDPOINTS.auth.token, {
    email,
    password,
  });

  saveTokens(response.data);
  return response.data;
}

export async function registerRequest({
  email,
  password,
  firstName,
  lastName,
}) {
  const response = await publicApi.post(API_ENDPOINTS.auth.register, {
    email,
    password,
    first_name: firstName,
    last_name: lastName,
  });

  return response.data;
}

export async function getCurrentUser() {
  const response = await api.get(API_ENDPOINTS.auth.me);
  return response.data;
}

export async function updateCurrentUser(payload) {
  const response = await api.patch(API_ENDPOINTS.auth.me, payload);
  return response.data;
}

export function logoutRequest() {
  clearTokens();
}
