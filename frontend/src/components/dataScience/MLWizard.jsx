"use client";

import { useMemo, useState } from "react";

const ALGORITHMS={
  CLASSIFICATION:[
    {value:"LOGISTIC_REGRESSION",label:"Logistic Regression",note:"Fast, interpretable baseline for classification."},
    {value:"RANDOM_FOREST_CLASSIFIER",label:"Random Forest",note:"Flexible non-linear model for more complex patterns."},
  ],
  REGRESSION:[
    {value:"LINEAR_REGRESSION",label:"Linear Regression",note:"Fast, interpretable baseline for numeric prediction."},
    {value:"RANDOM_FOREST_REGRESSOR",label:"Random Forest",note:"Handles non-linear relationships and interactions."},
  ],
};

export default function MLWizard({workspaceId,tables,onCreate,isSaving,onCancel}){
  const [step,setStep]=useState(1);
  const [advanced,setAdvanced]=useState(false);
  const [form,setForm]=useState({
    goal:"CLASSIFICATION",source_table:tables?.[0]?.id||"",name:"",description:"",
    target:"",features:[],algorithm:"LOGISTIC_REGRESSION",sample_limit:"",test_size:0.2,random_state:42,parameters:"{}"
  });
  const table=useMemo(()=>tables.find(t=>t.id===form.source_table),[tables,form.source_table]);
  const fields=table?.fields||[];
  const targetField=fields.find(f=>f.id===form.target);
  const algorithms=ALGORITHMS[form.goal]||[];

  function set(k,v){setForm(o=>({...o,[k]:v}));}
  function chooseGoal(goal){setForm(o=>({...o,goal,algorithm:ALGORITHMS[goal][0].value,target:"",features:[]}));}
  function changeTable(id){setForm(o=>({...o,source_table:id,target:"",features:[]}));}
  function toggleFeature(id){set("features",form.features.includes(id)?form.features.filter(x=>x!==id):[...form.features,id]);}
  function next(){
    if(step===2&&!form.source_table)return;
    if(step===3&&(!form.target||!form.features.length))return;
    setStep(s=>Math.min(5,s+1));
  }
  function submit(){
    let parameters={};
    try{parameters=JSON.parse(form.parameters||"{}");}catch{window.alert("Advanced parameters must be valid JSON.");return;}
    if(!form.name.trim()){window.alert("Give the model a name.");return;}
    onCreate({
      dataset:{
        workspace:workspaceId,
        name:`${form.name.trim()} · training data`,
        description:`Training dataset for ${form.name.trim()}`,
        source_table:form.source_table,
        filter_config:[],
        sample_limit:form.sample_limit===""?null:Number(form.sample_limit),
        enabled:true,
      },
      model:{
        workspace:workspaceId,
        name:form.name.trim(),
        description:form.description,
        task_type:form.goal,
        algorithm:form.algorithm,
        features:form.features,
        target:form.target,
        parameters,
        test_size:Number(form.test_size),
        random_state:Number(form.random_state),
        enabled:true,
      }
    });
  }

  return <div className="mlWizard">
    <div className="mlWizardSteps">
      {["Goal","Data","Target & features","Method","Review"].map((label,i)=><button key={label} type="button" className={step===i+1?"mlWizardStep active":step>i+1?"mlWizardStep done":"mlWizardStep"} onClick={()=>i+1<step&&setStep(i+1)}><span>{step>i+1?"✓":i+1}</span>{label}</button>)}
    </div>

    <div className="mlWizardBody">
      {step===1&&<div className="mlStepPanel">
        <p className="eyebrow">1 · Goal</p><h2>What do you want to predict?</h2><p>Choose the question first. Technical model settings come later.</p>
        <div className="mlGoalGrid">
          <button type="button" className={form.goal==="CLASSIFICATION"?"mlGoalCard selected":"mlGoalCard"} onClick={()=>chooseGoal("CLASSIFICATION")}><strong>Predict a category</strong><span>Yes / No, churn / retain, risk class, product class...</span><small>Classification</small></button>
          <button type="button" className={form.goal==="REGRESSION"?"mlGoalCard selected":"mlGoalCard"} onClick={()=>chooseGoal("REGRESSION")}><strong>Predict a number</strong><span>Revenue, demand, duration, cost, quantity...</span><small>Regression</small></button>
        </div>
      </div>}

      {step===2&&<div className="mlStepPanel">
        <p className="eyebrow">2 · Data</p><h2>Choose the training data</h2><p>ML training currently uses MANAGED tables so execution remains reproducible inside the platform.</p>
        <div className="mlTableGrid">{tables.map(t=><button type="button" key={t.id} className={form.source_table===t.id?"mlTableCard selected":"mlTableCard"} onClick={()=>changeTable(t.id)}><strong>{t.technical_name||t.table_name}</strong><span>{t.schema_name} · {t.fields?.length||0} fields</span><small>{t.data_source_name||"Managed source"}</small></button>)}</div>
        <label className="fieldGroup mlInlineField"><span>Training row limit <small>(optional)</small></span><input type="number" min="5" placeholder="Use all available rows" value={form.sample_limit} onChange={e=>set("sample_limit",e.target.value)}/></label>
      </div>}

      {step===3&&<div className="mlStepPanel">
        <p className="eyebrow">3 · Target & features</p><h2>What should the model learn?</h2>
        <div className="mlTargetFeatureLayout">
          <div><h3>Target</h3><p>The field you want to predict.</p><div className="mlFieldList">{fields.map(f=><button type="button" key={f.id} className={form.target===f.id?"mlField selected":"mlField"} onClick={()=>{set("target",f.id);set("features",form.features.filter(x=>x!==f.id));}}><strong>{f.business_name||f.name}</strong><small>{f.logical_type}</small></button>)}</div></div>
          <div><h3>Features</h3><p>The information the model may use.</p><div className="mlFieldList">{fields.filter(f=>f.id!==form.target).map(f=><label key={f.id} className={form.features.includes(f.id)?"mlField selected":"mlField"}><input type="checkbox" checked={form.features.includes(f.id)} onChange={()=>toggleFeature(f.id)}/><strong>{f.business_name||f.name}</strong><small>{f.logical_type}</small></label>)}</div></div>
        </div>
      </div>}

      {step===4&&<div className="mlStepPanel">
        <p className="eyebrow">4 · Method</p><h2>Choose how to train</h2><p>Start with the recommended baseline. Switch to Random Forest when you need a more flexible non-linear model.</p>
        <div className="mlAlgorithmGrid">{algorithms.map((a,i)=><button type="button" key={a.value} className={form.algorithm===a.value?"mlAlgorithmCard selected":"mlAlgorithmCard"} onClick={()=>set("algorithm",a.value)}><div><strong>{a.label}</strong>{i===0&&<span className="mlRecommended">Recommended baseline</span>}</div><p>{a.note}</p><small>{a.value}</small></button>)}</div>
        <button type="button" className="linkButton" onClick={()=>setAdvanced(!advanced)}>{advanced?"Hide advanced settings":"Advanced settings"}</button>
        {advanced&&<div className="mlAdvanced">
          <label className="fieldGroup"><span>Test size</span><input type="number" step=".05" min=".05" max=".5" value={form.test_size} onChange={e=>set("test_size",e.target.value)}/></label>
          <label className="fieldGroup"><span>Random state</span><input type="number" value={form.random_state} onChange={e=>set("random_state",e.target.value)}/></label>
          <label className="fieldGroup fullWidth"><span>Estimator parameters (JSON)</span><textarea className="codeArea" rows="5" value={form.parameters} onChange={e=>set("parameters",e.target.value)}/></label>
        </div>}
      </div>}

      {step===5&&<div className="mlStepPanel">
        <p className="eyebrow">5 · Review</p><h2>Ready to create the experiment</h2>
        <div className="mlReviewGrid">
          <div><span>Goal</span><strong>{form.goal==="CLASSIFICATION"?"Predict a category":"Predict a number"}</strong></div>
          <div><span>Data</span><strong>{table?table.table_name:"—"}</strong></div>
          <div><span>Target</span><strong>{targetField?.business_name||targetField?.name||"—"}</strong></div>
          <div><span>Features</span><strong>{form.features.length}</strong></div>
          <div><span>Method</span><strong>{algorithms.find(a=>a.value===form.algorithm)?.label}</strong></div>
          <div><span>Validation</span><strong>{Math.round(Number(form.test_size)*100)}% test set</strong></div>
        </div>
        <div className="formGrid">
          <label className="fieldGroup"><span>Model name</span><input value={form.name} onChange={e=>set("name",e.target.value)} placeholder="Customer churn model"/></label>
          <label className="fieldGroup fullWidth"><span>Description</span><textarea rows="2" value={form.description} onChange={e=>set("description",e.target.value)} placeholder="What decision will this model support?"/></label>
        </div>
        <div className="mlReviewNote"><strong>What will be created?</strong><span>A DatasetDefinition referencing the selected MANAGED table and a ModelDefinition linked to it. Training starts separately so you remain in control.</span></div>
      </div>}
    </div>

    <div className="mlWizardActions">
      <button type="button" className="button secondaryButton" onClick={step===1?onCancel:()=>setStep(s=>s-1)}>{step===1?"Cancel":"Back"}</button>
      {step<5?<button type="button" className="button primaryButton" onClick={next}>Continue</button>:<button type="button" className="button primaryButton" disabled={isSaving} onClick={submit}>{isSaving?"Creating...":"Create model"}</button>}
    </div>
  </div>;
}
