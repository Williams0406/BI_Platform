"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect,useMemo,useState } from "react";
import Icon from "@/components/ui/Icon";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { isNavigationItemActive,NAVIGATION_SECTIONS } from "@/lib/constants/navigation";
import { listModels } from "@/lib/services/dataScience";
import { listOptimizationModels } from "@/lib/services/optimization";

export default function Sidebar({open,onClose}){
  const pathname=usePathname();
  const {activeWorkspace,organizations}=useWorkspace();
  const organization=organizations.find(x=>x.id===activeWorkspace?.organization);
  const role=organization?.current_user_role;
  const canBuild=["OWNER","ADMIN","BUILDER"].includes(role);
  const canAdmin=["OWNER","ADMIN"].includes(role);
  const [intelligenceUsage,setIntelligenceUsage]=useState({ml:false,optimization:false,loaded:false});
  useEffect(()=>{
    let alive=true;
    if(!activeWorkspace?.id){setIntelligenceUsage({ml:false,optimization:false,loaded:true});return()=>{alive=false}}
    Promise.all([listModels(activeWorkspace.id).catch(()=>[]),listOptimizationModels(activeWorkspace.id).catch(()=>[])])
      .then(([ml,opt])=>{if(!alive)return;const mlRows=Array.isArray(ml)?ml:ml?.results||[];const optRows=Array.isArray(opt)?opt:opt?.results||[];setIntelligenceUsage({ml:mlRows.length>0,optimization:optRows.length>0,loaded:true})});
    return()=>{alive=false};
  },[activeWorkspace?.id]);

  const items=useMemo(()=>NAVIGATION_SECTIONS.flatMap(section=>{
    if(section.href)return [section];
    if(section.id==="advanced")return (section.items||[]).filter(item=>item.href==="/app/data-science"?intelligenceUsage.ml:intelligenceUsage.optimization);
    if(section.id==="manage")return (section.items||[]).filter(item=>{
      const movedToOptions=new Set(["/app/data-sources","/app/organizations","/app/governance","/app/customer-gateway","/app/environments","/app/operations","/app/import-export"]);
      if(movedToOptions.has(item.href))return false;
      return true;
    });
    return section.items||[];
  }),[intelligenceUsage,canAdmin,canBuild]);

  return <>
    {open&&<button type="button" className="sidebarBackdrop" onClick={onClose} aria-label="Close navigation"/>}
    <aside className={`sidebar iconOnlySidebar ${open?"sidebarOpen":""}`} aria-label="Primary navigation">
      <nav className="sidebarNav iconOnlyNav" aria-label="Primary navigation">
        {items.map(item=>{const active=isNavigationItemActive(pathname,item.href);return <Link key={item.href} className={`iconNavItem ${active?"iconNavItemActive":""}`} href={item.href} onClick={onClose} aria-current={active?"page":undefined} aria-label={item.label} data-tooltip={item.label}><Icon name={item.icon} size={21}/><span className="sidebarIconTooltip" role="tooltip">{item.label}</span></Link>})}
      </nav>
    </aside>
  </>
}
