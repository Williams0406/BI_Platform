"use client";
import {useSearchParams} from "next/navigation";
import DataTableWorkspace from "@/components/data/DataTableWorkspace";
export default function DataTablePage(){const search=useSearchParams();return <DataTableWorkspace initialTableId={search.get("table")||""}/>}
