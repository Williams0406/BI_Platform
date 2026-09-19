import ast, re

PLOT_CALLS=("plt.","sns.","matplotlib","seaborn","plotly","altair","chart(","bar(","line(")
ML_WORDS=("sklearn","xgboost","lightgbm","catboost","tensorflow","torch","RandomForest","fit(","predict(")
OPT_WORDS=("ortools","pyomo","pulp","cvxpy","gurobi","cplex","scipy.optimize","minimize(","maximize(","Solve(","solve(")

def analyze_python(code):
    out=[]
    try: tree=ast.parse(code)
    except SyntaxError as e: return {"valid":False,"error":str(e),"artifacts":[]}
    for n in ast.walk(tree):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)): out.append({"type":"FUNCTION","name":n.name})
        if isinstance(n,(ast.Assign,ast.AnnAssign)):
            targets=n.targets if isinstance(n,ast.Assign) else [n.target]
            src=ast.get_source_segment(code,n) or ""
            for t in targets:
                if isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name):
                    key=t.slice.value if isinstance(t.slice,ast.Constant) else None
                    out.append({"type":"FIELD_RULE","name":f"{t.value.id}.{key}" if key else t.value.id,"table":t.value.id,"field":key,"rule_source":src})
                elif isinstance(t,ast.Name):
                    metric_candidate=bool(re.search(r"\.(sum|mean|median|min|max|count|nunique|score)\s*\(|(accuracy|precision|recall|f1|roc_auc|mean_squared|mean_absolute|r2)_",src,re.I))
                    literal=isinstance(getattr(n,"value",None),(ast.Constant,ast.BinOp,ast.UnaryOp))
                    if metric_candidate or literal:
                        out.append({"type":"VARIABLE","name":t.id,"metric_candidate":True,"expression":src})
    low=code.lower()
    if any(x.lower() in low for x in PLOT_CALLS): out.append({"type":"CHART","name":"Python figure"})
    if any(x.lower() in low for x in ML_WORDS): out.append({"type":"ML_MODEL","name":"Python ML model"})
    if any(x.lower() in low for x in OPT_WORDS): out.append({"type":"OPTIMIZATION","name":"Python optimization"})
    if not out and code.strip(): out.append({"type":"TRANSFORMATION","name":"Python transformation"})
    return {"valid":True,"artifacts":dedupe(out)}

def analyze_sql(code):
    u=code.upper(); out=[]
    if re.search(r"\b(UPDATE|INSERT|DELETE|MERGE|ALTER|CREATE|DROP)\b",u): out.append({"type":"TRANSFORMATION","name":"SQL transformation"})
    if re.search(r"\b(SUM|AVG|COUNT|MIN|MAX)\s*\(",u) and "GROUP BY" not in u:
        m=re.search(r"\bAS\s+([A-Za-z_][\w]*)",code,re.I); out.append({"type":"MEASURE","name":m.group(1) if m else "SQL measure"})
    if not out and re.search(r"\bSELECT\b",u): out.append({"type":"DATASET","name":"SQL dataset"})
    return {"valid":bool(code.strip()),"artifacts":dedupe(out)}

def analyze_dax(code):
    out=[]; text=code.strip()
    m=re.search(r"^\s*MEASURE\s+([^=]+)=",text,re.I|re.M)
    c=re.search(r"^\s*COLUMN\s+([^=]+)=",text,re.I|re.M)
    if m: out.append({"type":"MEASURE","name":m.group(1).strip()})
    elif c: out.append({"type":"FIELD_RULE","name":c.group(1).strip()})
    elif "=" in text: out.append({"type":"MEASURE","name":text.split("=",1)[0].strip()})
    elif text: out.append({"type":"MEASURE","name":"DAX measure"})
    return {"valid":bool(text),"artifacts":out}

def dedupe(items):
    seen=set(); result=[]
    for x in items:
        k=(x.get("type"),x.get("name"))
        if k not in seen: seen.add(k); result.append(x)
    return result

def analyze(language,code):
    return {"PYTHON":analyze_python,"SQL":analyze_sql,"DAX":analyze_dax}.get(language.upper(),lambda c:{"valid":False,"artifacts":[]})(code)
