"use client";

import { useContext } from "react";

import { WorkspaceContext } from "@/lib/context/WorkspaceContext";

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error("useWorkspace debe utilizarse dentro de WorkspaceProvider.");
  }
  return context;
}
