"use client";

import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import OperationalViewBuilder from "@/components/views/OperationalViewBuilder";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { getCatalogTable, listCatalogTables } from "@/lib/services/dataModel";
import { listDataSources } from "@/lib/services/dataSources";
import { listMetrics, listSemanticModels } from "@/lib/services/metrics";
import { getView, getViewSchema, validateView } from "@/lib/services/views";
import { getApiErrorMessage } from "@/lib/utils/errors";

const WRITE_ROLES=["OWNER","ADMIN","BUILDER"];
const asList=v=>Array.isArray(v)?v:v?.results||[];
export default function ViewDetailPage(){
 const params=useParams();const {activeWorkspace,organizations}=useWorkspace();const [view,setView]=useState(null),[schema,setSchema]=useState(null),[table,setTable]=useState(null),[tables,setTables]=useState([]),[models,setModels]=useState([]),[metrics,setMetrics]=useState([]),[sources,setSources]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState("");
 const organization=useMemo(()=>organizations.find(x=>x.id===activeWorkspace?.organization),[organizations,activeWorkspace]);const canWrite=WRITE_ROLES.includes(organization?.current_user_role);const sourceById=useMemo(()=>Object.fromEntries(sources.map(s=>[s.id,s])),[sources]);
 async function load(){if(!params.id||!activeWorkspace?.id)return;setLoading(true);setError("");try{const definition=await getView(params.id);const sourceList=asList(await listDataSources(activeWorkspace.id));const [schemaData,contract,sourceTable,tableGroups,modelData,metricData]=await Promise.all([getViewSchema(params.id),validateView(params.id),getCatalogTable(definition.source_table),Promise.all(sourceList.map(s=>listCatalogTables(s.id).catch(()=>[]))),listSemanticModels(activeWorkspace.id).catch(()=>[]),listMetrics(activeWorkspace.id).catch(()=>[])]);setView(definition);setSchema({...schemaData,contract});setTable(sourceTable);setSources(sourceList);setTables(tableGroups.flatMap(asList));setModels(asList(modelData));setMetrics(asList(metricData))}catch(e){setError(getApiErrorMessage(e))}finally{setLoading(false)}}
 useEffect(()=>{load()},[params.id,activeWorkspace?.id]);
 if(loading&&!view)return <Spinner label="Opening Operational View Studio…"/>;if(!view||!schema||!table)return <EmptyState title="View unavailable" description={error||"The view could not be loaded."}/>;
 return <div className="ovBuilderPage"><OperationalViewBuilder view={view} table={table} tables={tables} models={models} metrics={metrics} sourceById={sourceById} schema={schema} canWrite={canWrite} onSaved={load}/></div>
}
