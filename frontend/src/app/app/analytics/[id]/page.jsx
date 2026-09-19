"use client";

import { useEffect, useState } from "react";
import ExploreStudio from "@/components/explore/ExploreStudio";

export default function ChartDetailPage({ params }) {
  const [id, setId] = useState(null);
  useEffect(() => { Promise.resolve(params).then((value) => setId(value.id)); }, [params]);
  if (!id) return null;
  return <ExploreStudio chartId={id} />;
}
