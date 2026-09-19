"use client";

import { createContext, useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/lib/hooks/useAuth";
import { listOrganizations, listWorkspaces } from "@/lib/services/workspaces";
import {
  clearStoredWorkspaceId,
  getStoredWorkspaceId,
  storeWorkspaceId,
} from "@/lib/storage/workspace";

export const WorkspaceContext = createContext(null);

export function WorkspaceProvider({ children }) {
  const { isAuthenticated, isInitializing: authInitializing } = useAuth();
  const [organizations, setOrganizations] = useState([]);
  const [workspaces, setWorkspaces] = useState([]);
  const [activeWorkspace, setActiveWorkspaceState] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const selectInitialWorkspace = useCallback((items) => {
    const storedId = getStoredWorkspaceId();
    const stored = storedId ? items.find((item) => item.id === storedId) : null;
    const next = stored || items.find((item) => item.status === "ACTIVE") || items[0] || null;

    setActiveWorkspaceState(next);
    if (next) storeWorkspaceId(next.id);
    else clearStoredWorkspaceId();
    return next;
  }, []);

  const refresh = useCallback(async () => {
    if (!isAuthenticated) {
      setOrganizations([]);
      setWorkspaces([]);
      setActiveWorkspaceState(null);
      clearStoredWorkspaceId();
      return;
    }

    setIsLoading(true);
    setError("");
    try {
      const [organizationData, workspaceData] = await Promise.all([
        listOrganizations(),
        listWorkspaces(),
      ]);
      setOrganizations(organizationData);
      setWorkspaces(workspaceData);

      setActiveWorkspaceState((current) => {
        if (current) {
          const refreshed = workspaceData.find((item) => item.id === current.id);
          if (refreshed) {
            storeWorkspaceId(refreshed.id);
            return refreshed;
          }
        }
        const storedId = getStoredWorkspaceId();
        const stored = storedId
          ? workspaceData.find((item) => item.id === storedId)
          : null;
        const next =
          stored ||
          workspaceData.find((item) => item.status === "ACTIVE") ||
          workspaceData[0] ||
          null;
        if (next) storeWorkspaceId(next.id);
        else clearStoredWorkspaceId();
        return next;
      });
    } catch (requestError) {
      setError(requestError);
      throw requestError;
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (authInitializing) return;
    refresh().catch(() => {});
  }, [authInitializing, refresh]);

  const setActiveWorkspace = useCallback(
    (workspaceOrId) => {
      const next =
        typeof workspaceOrId === "string"
          ? workspaces.find((item) => item.id === workspaceOrId) || null
          : workspaceOrId;

      setActiveWorkspaceState(next);
      if (next?.id) storeWorkspaceId(next.id);
      else clearStoredWorkspaceId();
    },
    [workspaces],
  );

  const value = useMemo(
    () => ({
      organizations,
      workspaces,
      activeWorkspace,
      activeWorkspaceId: activeWorkspace?.id || null,
      isLoading,
      error,
      refresh,
      setActiveWorkspace,
      selectInitialWorkspace,
    }),
    [
      organizations,
      workspaces,
      activeWorkspace,
      isLoading,
      error,
      refresh,
      setActiveWorkspace,
      selectInitialWorkspace,
    ],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}
