"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import Breadcrumbs from "@/components/layout/Breadcrumbs";
import Icon from "@/components/ui/Icon";
import ActivityPanel from "@/components/workspace/ActivityPanel";
import CreateMenu from "@/components/workspace/CreateMenu";
import GlobalSearch from "@/components/workspace/GlobalSearch";
import { ROUTES } from "@/lib/constants/routes";
import { useAuth } from "@/lib/hooks/useAuth";
import { useWorkspace } from "@/lib/hooks/useWorkspace";
import { displayName, initials } from "@/lib/utils/formatters";

export default function Topbar({ onMenuClick }) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { organizations, workspaces, activeWorkspace, setActiveWorkspace, isLoading } = useWorkspace();
  const [searchOpen, setSearchOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(false);

  const activeOrganization = useMemo(
    () => organizations.find((item) => item.id === activeWorkspace?.organization),
    [organizations, activeWorkspace],
  );
  const role = activeOrganization?.current_user_role;
  const canBuild = ["OWNER","ADMIN","BUILDER"].includes(role);
  const canAdminister = ["OWNER","ADMIN"].includes(role);

  useEffect(() => {
    const handler = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen(true);
        setCreateOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  function handleLogout() {
    logout();
    router.replace(ROUTES.LOGIN);
  }

  return (
    <>
      <header className="topbar">
        <div className="topbarLeft">
          <button type="button" className="iconButton menuButton" onClick={onMenuClick} aria-label="Open navigation">
            <Icon name="menu" size={19} />
          </button>
          <div className="topbarContext">
            <Breadcrumbs />
            <div className="workspaceSelectorWrap">
              {workspaces.length ? (
                <select className="workspaceSelector" value={activeWorkspace?.id || ""} onChange={(event) => setActiveWorkspace(event.target.value)} disabled={isLoading} aria-label="Seleccionar workspace activo">
                  {workspaces.map((workspace) => <option value={workspace.id} key={workspace.id}>{workspace.name}</option>)}
                </select>
              ) : <Link className="workspaceEmptyLink" href={ROUTES.WORKSPACES}>Crear workspace</Link>}
              {activeOrganization?.current_user_role ? <span className="rolePill">{activeOrganization.current_user_role}</span> : null}
            </div>
          </div>
        </div>

        <div className="topbarActions">
          <button type="button" className="topbarSearchButton" onClick={() => setSearchOpen(true)} type="button"><Icon name="explore" size={17}/><span>Search</span><kbd>Ctrl K</kbd></button>
          {canBuild ? <div className="createMenuWrap"><button className="button buttonPrimary topbarCreate" type="button" onClick={()=>setCreateOpen(v=>!v)}>+ Create</button><CreateMenu open={createOpen} onClose={()=>setCreateOpen(false)}/></div> : null}
          <button type="button" className="iconButton" onClick={()=>setActivityOpen(true)} title="Activity" aria-label="Activity"><Icon name="activity" size={18}/></button>
          {canAdminister ? <Link className="iconButton desktopOnly" href="/app/operations" title="Platform health" aria-label="Platform health"><Icon name="pulse" size={18}/></Link> : null}
          <div className="topbarDivider" />
          <div className="userMenu">
            <div className="avatar">{initials(user)}</div>
            <div className="userIdentity"><strong>{displayName(user)}</strong><span>{user?.email}</span></div>
            <button type="button" className="iconButton" onClick={handleLogout} title="Sign out" aria-label="Sign out"><Icon name="logout" size={18} /></button>
          </div>
        </div>
      </header>
      <GlobalSearch open={searchOpen} onClose={()=>setSearchOpen(false)}/>
      <ActivityPanel open={activityOpen} onClose={()=>setActivityOpen(false)}/>
    </>
  );
}
