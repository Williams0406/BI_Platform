const ACCESS_TOKEN_KEY = "bi_access_token";
const REFRESH_TOKEN_KEY = "bi_refresh_token";

function canUseStorage() {
  return typeof window !== "undefined" && Boolean(window.localStorage);
}

export function getAccessToken() {
  if (!canUseStorage()) return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken() {
  if (!canUseStorage()) return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function saveTokens({ access, refresh }) {
  if (!canUseStorage()) return;

  if (access) {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, access);
  }

  if (refresh) {
    window.localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  }
}

export function clearTokens() {
  if (!canUseStorage()) return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function hasSessionTokens() {
  return Boolean(getAccessToken() || getRefreshToken());
}
