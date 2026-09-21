"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect,useMemo,useState } from "react";
import Icon from "@/components/ui/Icon";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { getNavigationGroupForPath,isNavigationItemActive,NAVIGATION_SECTIONS } from "@/lib/constants/navigation";
import { listModels } from "@/lib/services/dataScience";
import { listOptimizationModels } from "@/lib/services/optimization";

export default function Sidebar({open,onClose,collapsed=false,onToggleCollapse}){
  const pathname=usePathname();
  const {activeWorkspace,organizations}=useWorkspace();
  const organization=organizations.find(x=>x.id===activeWorkspace?.organization);
  const role=organization?.current_user_role;
  const canBuild=["OWNER","ADMIN","BUILDER"].includes(role);
  const canAdmin=["OWNER","ADMIN"].includes(role);
  const activeGroup=useMemo(()=>getNavigationGroupForPath(pathname),[pathname]);
  const [expanded,setExpanded]=useState(activeGroup?.id||"");
  const [intelligenceUsage,setIntelligenceUsage]=useState({ml:false,optimization:false,loaded:false});
  useEffect(()=>{if(activeGroup?.id)setExpanded(activeGroup.id);},[activeGroup?.id]);
  useEffect(()=>{
    let alive=true;
    if(!activeWorkspace?.id){setIntelligenceUsage({ml:false,optimization:false,loaded:true});return()=>{alive=false}}
    Promise.all([listModels(activeWorkspace.id).catch(()=>[]),listOptimizationModels(activeWorkspace.id).catch(()=>[])])
      .then(([ml,opt])=>{if(!alive)return;const mlRows=Array.isArray(ml)?ml:ml?.results||[];const optRows=Array.isArray(opt)?opt:opt?.results||[];setIntelligenceUsage({ml:mlRows.length>0,optimization:optRows.length>0,loaded:true})});
    return()=>{alive=false};
  },[activeWorkspace?.id]);
  return <>
    {open&&<button type="button" className="sidebarBackdrop" onClick={onClose} aria-label="Close navigation"/>}
    <aside className={`sidebar ${open?"sidebarOpen":""} ${collapsed?"sidebarCollapsed":""}`} aria-label="Primary navigation">
      <div className="sidebarBrandRow"><Link className="sidebarBrand" href="/app" onClick={onClose}><div className="brandMark brandMarkShell">BI</div><div className="sidebarBrandCopy"><strong>Intelligence</strong><span>Decision workspace</span></div></Link><button type="button" className="sidebarCollapseButton" onClick={onToggleCollapse} aria-label={collapsed?"Expand sidebar":"Collapse sidebar"} title={collapsed?"Expand sidebar":"Collapse sidebar"}><Icon name="chevronDown" size={16}/></button></div>
      <nav className="sidebarNav" aria-label="Primary navigation">
        {NAVIGATION_SECTIONS.map(section=>{
          if(section.id==="advanced" && intelligenceUsage.loaded && !intelligenceUsage.ml && !intelligenceUsage.optimization)return null;
          if(section.href){const active=isNavigationItemActive(pathname,section.href);return <Link key={section.id} className={`navPrimaryItem ${active?"navPrimaryItemActive":""}`} href={section.href} onClick={onClose} aria-current={active?"page":undefined}><Icon name={section.icon} size={18}/><span>{section.label}</span></Link>}
          const visible=section.id==="advanced"?section.items.filter(item=>item.href==="/app/data-science"?intelligenceUsage.ml:intelligenceUsage.optimization):section.id==="manage"?section.items.filter(item=>{
            if(["/app/governance","/app/customer-gateway","/app/operations"].includes(item.href))return canAdmin;
            if(item.href==="/app/import-export")return canBuild;
            return true;
          }):section.items;
          const active=visible.some(item=>isNavigationItemActive(pathname,item.href));
          const isOpen=expanded===section.id;
          return <div className={`navGroup ${active?"navGroupActive":""}`} key={section.id}>
            <button type="button" className="navGroupButton" aria-expanded={isOpen} onClick={()=>{if(collapsed){onToggleCollapse?.();setExpanded(section.id);}else setExpanded(v=>v===section.id?"":section.id)}}><span className="navGroupButtonMain"><Icon name={section.icon} size={18}/><span>{section.label}</span></span><Icon name="chevronDown" size={15} className={`navChevron ${isOpen?"navChevronOpen":""}`}/></button>
            {isOpen&&<div className="navChildren">{visible.map(item=>{const itemActive=isNavigationItemActive(pathname,item.href);return <Link key={item.href} className={`navChildItem ${itemActive?"navChildItemActive":""}`} href={item.href} onClick={onClose} aria-current={itemActive?"page":undefined}><Icon name={item.icon} size={16}/><span>{item.label}</span></Link>})}</div>}
          </div>
        })}
      </nav>
      <div className="sidebarFooter"><p>DATA → ANALYZE → DECIDE</p><span>Focused workspace</span></div>
    </aside>
  </>
}
