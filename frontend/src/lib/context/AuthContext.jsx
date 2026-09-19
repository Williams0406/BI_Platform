"use client";

import { createContext, useCallback, useEffect, useMemo, useState } from "react";

import { clearTokens, hasSessionTokens } from "@/lib/auth/tokens";
import {
  getCurrentUser,
  loginRequest,
  logoutRequest,
  registerRequest,
} from "@/lib/services/auth";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isInitializing, setIsInitializing] = useState(true);

  const loadUser = useCallback(async () => {
    if (!hasSessionTokens()) {
      setUser(null);
      return null;
    }

    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      return currentUser;
    } catch (error) {
      clearTokens();
      setUser(null);
      throw error;
    }
  }, []);

  useEffect(() => {
    let mounted = true;

    async function bootstrap() {
      try {
        if (hasSessionTokens()) {
          const currentUser = await getCurrentUser();
          if (mounted) setUser(currentUser);
        }
      } catch {
        clearTokens();
        if (mounted) setUser(null);
      } finally {
        if (mounted) setIsInitializing(false);
      }
    }

    bootstrap();

    function handleForcedLogout() {
      clearTokens();
      setUser(null);
      setIsInitializing(false);
    }

    window.addEventListener("auth:logout", handleForcedLogout);

    return () => {
      mounted = false;
      window.removeEventListener("auth:logout", handleForcedLogout);
    };
  }, []);

  const login = useCallback(async ({ email, password }) => {
    await loginRequest({ email, password });
    const currentUser = await getCurrentUser();
    setUser(currentUser);
    return currentUser;
  }, []);

  const register = useCallback(async (payload) => {
    await registerRequest(payload);
    await loginRequest({ email: payload.email, password: payload.password });
    const currentUser = await getCurrentUser();
    setUser(currentUser);
    return currentUser;
  }, []);

  const logout = useCallback(() => {
    logoutRequest();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isInitializing,
      login,
      register,
      logout,
      reloadUser: loadUser,
      setUser,
    }),
    [user, isInitializing, login, register, logout, loadUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
