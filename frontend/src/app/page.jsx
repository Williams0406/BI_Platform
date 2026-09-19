"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import Spinner from "@/components/ui/Spinner";
import { ROUTES } from "@/lib/constants/routes";
import { useAuth } from "@/lib/hooks/useAuth";

export default function HomePage() {
  const router = useRouter();
  const { isAuthenticated, isInitializing } = useAuth();

  useEffect(() => {
    if (!isInitializing) {
      router.replace(isAuthenticated ? ROUTES.APP : ROUTES.LOGIN);
    }
  }, [isAuthenticated, isInitializing, router]);

  return (
    <main className="fullscreenCenter">
      <Spinner label="Abriendo plataforma..." />
    </main>
  );
}
