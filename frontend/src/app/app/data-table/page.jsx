"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";

import DataTableWorkspace from "@/components/data/DataTableWorkspace";

function DataTablePageContent() {
  const search = useSearchParams();

  return <DataTableWorkspace initialTableId={search.get("table") || ""} />;
}

export default function DataTablePage() {
  return (
    <Suspense fallback={null}>
      <DataTablePageContent />
    </Suspense>
  );
}
