import axios from "axios";

import { API_ENDPOINTS } from "@/lib/api/endpoints";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  saveTokens,
} from "@/lib/auth/tokens";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

export const publicApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

let refreshPromise = null;

function emitAuthLogout() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("auth:logout"));
  }
}

async function refreshAccessToken() {
  const refresh = getRefreshToken();

  if (!refresh) {
    throw new Error("No refresh token available.");
  }

  const response = await publicApi.post(API_ENDPOINTS.auth.refresh, { refresh });
  const access = response.data?.access;
  const rotatedRefresh = response.data?.refresh;

  if (!access) {
    throw new Error("The backend did not return a refreshed access token.");
  }

  saveTokens({ access, refresh: rotatedRefresh || refresh });
  return access;
}

api.interceptors.request.use((config) => {
  const access = getAccessToken();

  if (access) {
    config.headers.Authorization = `Bearer ${access}`;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;

    if (
      status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
      originalRequest.url?.includes(API_ENDPOINTS.auth.refresh)
    ) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
      }

      const access = await refreshPromise;
      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${access}`;

      return api(originalRequest);
    } catch (refreshError) {
      clearTokens();
      emitAuthLogout();
      return Promise.reject(refreshError);
    }
  },
);

export default api;
