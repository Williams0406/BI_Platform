"use client";

import Link from "next/link";
import Icon from "@/components/ui/Icon";
import { useWorkspace } from "@/lib/hooks/useWorkspace";

const ITEMS=[
  ["Connect data","plug","/app/data-sources"],["Import file","transfer","/app/import-export"],["Code block","code","/app/scripts"],
  ["Analytics","explore","/app/analytics"],["ML model","brain","/app/data-science"],["Optimization model","optimize","/app/optimization"]
];
const BUILD_ROLES=["OWNER","ADMIN","BUILDER"];

export default function CreateMenu({open,onClose}){
  const {activeWorkspace,organizations}=useWorkspace();
  const org=organizations.find(x=>x.id===activeWorkspace?.organization);
  if(!open || !BUILD_ROLES.includes(org?.current_user_role))return null;
  return <div className="createPopover"><p>Create</p>{ITEMS.map(([label,icon,href])=><Link href={href} onClick={onClose} key={label}><Icon name={icon} size={17}/><span>{label}</span></Link>)}</div>;
}
