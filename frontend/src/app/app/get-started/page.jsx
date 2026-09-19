"use client";

import Link from "next/link";
import WorkspaceSetupGuide from "@/components/onboarding/WorkspaceSetupGuide";
import EmptyState from "@/components/ui/EmptyState";
import { useWorkspace } from "@/lib/hooks/useWorkspace";

const roleHelp={
  OWNER:{title:"Own the workspace",text:"You can build the analytical workflow and administer organization-level governance."},
  ADMIN:{title:"Administer and build",text:"You can configure workspace data, build content and manage governance controls."},
  BUILDER:{title:"Build analytics",text:"You can connect and prepare data, define metrics, create analyses, dashboards, ML and optimization models."},
  ANALYST:{title:"Analyze trusted content",text:"Your experience emphasizes existing governed data and shared analytical content rather than setup controls."},
  VIEWER:{title:"Consume trusted decisions",text:"Your experience emphasizes catalog context, dashboards and approved outputs rather than authoring controls."},
};

export default function GetStartedPage(){
  const {activeWorkspace,organizations}=useWorkspace();
  if(!activeWorkspace)return <EmptyState title="Select a workspace" description="The setup guide needs an active workspace."/>;
  const organization=organizations.find(x=>x.id===activeWorkspace.organization);
  const role=organization?.current_user_role;
  const help=roleHelp[role]||{title:"Workspace access",text:"Available actions follow your organization role."};
  const canAdminister=["OWNER","ADMIN"].includes(role);
  return <div className="pageStack onboardingPage">
    <header className="pageHeader"><div><p className="eyebrow">GET STARTED</p><h1>{activeWorkspace.name}</h1><p>Use the shortest supported path to a useful result. Technical engines remain available when you need them, but they are not prerequisites to understanding the product.</p></div></header>
    <section className="onboardingRoleCard"><div><small>YOUR ROLE</small><strong>{role||"—"}</strong></div><div><h2>{help.title}</h2><p>{help.text}</p></div><Link href="/app/manage">Review workspace access →</Link></section>
    <WorkspaceSetupGuide activeWorkspace={activeWorkspace} role={role} variant="full"/>
    <section className="onboardingPaths">
      <div className="sectionHeading"><div><p className="eyebrow">AFTER THE CORE PATH</p><h2>Choose the capability your decision needs</h2></div></div>
      <div className="onboardingPathGrid">
        <Link href="/app/data-science"><strong>Predict</strong><span>Use guided Machine Learning when the next decision depends on an unknown future category or number.</span><em>Machine Learning →</em></Link>
        <Link href="/app/optimization"><strong>Optimize</strong><span>Use mathematical optimization when you know the objective, decisions and constraints and need the best feasible plan.</span><em>Optimization →</em></Link>
        {canAdminister ? <Link href="/app/governance"><strong>Govern</strong><span>Control usage, retention, auditability and explicit access when you administer the workspace.</span><em>Governance →</em></Link> : <Link href="/app/data-assets"><strong>Understand trusted data</strong><span>Use Catalog and lineage context to understand where analytical content comes from.</span><em>Catalog →</em></Link>}
      </div>
    </section>
    <section className="onboardingPrinciples">
      <h2>How this workspace is organized</h2>
      <div><strong>Data</strong><span>What information is available?</span></div>
      <div><strong>Prepare</strong><span>Does the data need reusable transformation?</span></div>
      <div><strong>Analyze</strong><span>What does the data tell us?</span></div>
      <div><strong>Dashboards</strong><span>What should others monitor?</span></div>
      <div><strong>AI & Optimization</strong><span>What may happen, or what should we do?</span></div>
      <div><strong>Manage</strong><span>Who can do what, under which controls?</span></div>
    </section>
  </div>;
}
