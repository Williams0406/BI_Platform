import { Suspense } from "react";
import AppShell from "@/components/layout/AppShell";

export default function ProtectedAppLayout({ children }) {
  return (
    <Suspense fallback={null}>
      <AppShell>{children}</AppShell>
    </Suspense>
  );
}
