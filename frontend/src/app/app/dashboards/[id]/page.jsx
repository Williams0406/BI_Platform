"use client";
import { useEffect,useMemo,useState } from "react";
import DashboardBuilder from "@/components/analytics/DashboardBuilder";
import EmptyState from "@/components/ui/EmptyState";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
const WRITE_ROLES=["OWNER","ADMIN","BUILDER"];
export default function DashboardDetailPage({params}){const {activeWorkspace,organizations}=useWorkspace();const [id,setId]=useState(null);useEffect(()=>{Promise.resolve(params).then(p=>setId(p.id));},[params]);const org=useMemo(()=>organizations.find(o=>o.id===activeWorkspace?.organization),[organizations,activeWorkspace]);if(!activeWorkspace)return <EmptyState title="Select a workspace" description="Dashboards belong to a workspace."/>;if(!id)return null;return <DashboardBuilder dashboardId={id} workspaceId={activeWorkspace.id} canWrite={WRITE_ROLES.includes(org?.current_user_role)}/>;}
