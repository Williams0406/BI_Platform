"use client";
import { useState } from "react";
import { usePathname } from "next/navigation";
import AuthGuard from "@/components/auth/AuthGuard";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";
import GlobalOptionsBar from "@/components/layout/GlobalOptionsBar";
export default function AppShell({children}){
 const [sidebarOpen,setSidebarOpen]=useState(false); const pathname=usePathname();
 const platformSettingsPaths=["/app/data-sources","/app/organizations","/app/governance","/app/customer-gateway","/app/environments","/app/operations","/app/import-export"];
 const platformSettingsPage=platformSettingsPaths.some(base=>pathname===base||pathname.startsWith(`${base}/`));
 const fullBleedWorkspace = pathname === "/app/data" || pathname === "/app/data-table" || pathname === "/app/analytics" || pathname.startsWith("/app/analytics/") || pathname.startsWith("/app/reports/") || pathname === "/app/views" || pathname.startsWith("/app/views/") || pathname === "/app/scripts";
 return <AuthGuard><div className="appShell sidebarIconsOnly"><a className="skipLink" href="#main-content">Skip to main content</a><Sidebar open={sidebarOpen} onClose={()=>setSidebarOpen(false)}/><div className="appMain"><Topbar onMenuClick={()=>setSidebarOpen(true)}/><GlobalOptionsBar/><main className={`pageContent ${fullBleedWorkspace?"workspaceFullBleed":""} ${platformSettingsPage?"platformSettingsContent":""}`} id="main-content" tabIndex={-1}>{children}</main></div></div></AuthGuard>
}
