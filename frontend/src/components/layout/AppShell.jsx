"use client";
import { useEffect,useState } from "react";
import { usePathname,useSearchParams } from "next/navigation";
import AuthGuard from "@/components/auth/AuthGuard";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";
export default function AppShell({children}){
 const [sidebarOpen,setSidebarOpen]=useState(false);
 const [sidebarCollapsed,setSidebarCollapsed]=useState(false);
 const pathname=usePathname();const search=useSearchParams();
 useEffect(()=>{try{setSidebarCollapsed(localStorage.getItem("bi:sidebar-collapsed")==="1")}catch{}},[]);
 function toggleSidebar(){setSidebarCollapsed(v=>{const next=!v;try{localStorage.setItem("bi:sidebar-collapsed",next?"1":"0")}catch{}return next})}
 const fullscreen=search.get("fullscreen")==="1"&&(pathname.startsWith("/app/dashboards/")||pathname.startsWith("/app/reports/"));
 const fullBleedWorkspace = pathname === "/app/data" || pathname === "/app/data-model" || pathname === "/app/data-table" || pathname === "/app/analytics" || pathname.startsWith("/app/analytics/");
 return <AuthGuard>{fullscreen?<div className="fullscreenApp"><main id="main-content" tabIndex={-1}>{children}</main></div>:<div className={`appShell ${sidebarCollapsed?"sidebarIsCollapsed":""}`}><a className="skipLink" href="#main-content">Skip to main content</a><Sidebar open={sidebarOpen} onClose={()=>setSidebarOpen(false)} collapsed={sidebarCollapsed} onToggleCollapse={toggleSidebar}/><div className="appMain"><Topbar onMenuClick={()=>setSidebarOpen(true)}/><main className={`pageContent ${fullBleedWorkspace?"workspaceFullBleed":""}`} id="main-content" tabIndex={-1}>{children}</main></div></div>}</AuthGuard>
}
