"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import Spinner from "@/components/ui/Spinner";
import { ROUTES } from "@/lib/constants/routes";
import { useAuth } from "@/lib/hooks/useAuth";

export default function AuthGuard({ children }) {
  const router = useRouter();
  const { isAuthenticated, isInitializing } = useAuth();

  useEffect(() => {
    if (!isInitializing && !isAuthenticated) {
      router.replace(ROUTES.LOGIN);
    }
  }, [isInitializing, isAuthenticated, router]);

  if (isInitializing || !isAuthenticated) {
    return (
      <main className="fullscreenCenter">
        <Spinner label="Validando sesión..." />
      </main>
    );
  }

  return children;
}
