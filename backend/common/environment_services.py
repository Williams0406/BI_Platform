from __future__ import annotations
import json, os, re, subprocess, sys, time, urllib.request, urllib.parse
from html.parser import HTMLParser
from pathlib import Path
from django.conf import settings

_CACHE={"at":0.0,"names":[]}
PACKAGE_ALIASES={"sklearn":"scikit-learn"}
IMPORT_ALIASES={
    "scikit-learn":"sklearn",
    "pillow":"PIL",
    "opencv-python":"cv2",
    "pyyaml":"yaml",
}
class _SimpleParser(HTMLParser):
    def __init__(self): super().__init__(); self.names=[]
    def handle_data(self,data):
        s=data.strip()
        if s and re.fullmatch(r"[A-Za-z0-9_.-]+",s): self.names.append(s)

def canonical_package_name(name:str):
    raw=(name or "").strip()
    return PACKAGE_ALIASES.get(raw.lower(),raw)

def import_name_for_package(name:str):
    canonical=canonical_package_name(name)
    return IMPORT_ALIASES.get(canonical.lower(),canonical.replace("-","_"))

def search_pypi(query:str, limit:int=60):
    q=(query or "").strip().lower()
    if not q: return []
    canonical=PACKAGE_ALIASES.get(q,q)
    exact=[]
    try:
        info=pypi_package(canonical)
        exact=[{"name":info["name"],"source":"PYPI"}]
    except Exception:
        pass
    now=time.time()
    if _CACHE["names"] and now-_CACHE["at"]<=21600:
        names=_CACHE["names"]
        starts=[n for n in names if n.lower().startswith(q)]
        contains=[n for n in names if q in n.lower() and n not in starts]
        merged=[]; seen=set()
        for item in exact+[{"name":n,"source":"PYPI"} for n in (starts+contains)]:
            key=item["name"].lower()
            if key not in seen: seen.add(key); merged.append(item)
        return merged[:limit]
    return exact[:limit]

def pypi_package(name:str):
    name=canonical_package_name(name)
    safe=urllib.parse.quote(name)
    url=f"https://pypi.org/pypi/{safe}/json"
    req=urllib.request.Request(url,headers={"User-Agent":"BI-Platform/1.0"})
    with urllib.request.urlopen(req,timeout=15) as r: data=json.loads(r.read().decode())
    info=data.get("info") or {}; releases=data.get("releases") or {}; versions=list(releases.keys())
    try:
        from packaging.version import Version
        versions=sorted(versions,key=Version,reverse=True)
    except Exception: versions=sorted(versions,reverse=True)
    return {"name":info.get("name") or name,"version":info.get("version") or "","summary":info.get("summary") or "","versions":versions[:100],"home_page":info.get("project_url") or info.get("home_page") or ""}

def _short_environment_dir(environment):
    # Keep Windows paths deliberately short. Some wheels (notably scikit-learn)
    # contain deeply nested files and can fail halfway through installation when
    # the venv itself already lives under multiple UUID directories.
    env_id=str(environment.id).replace("-","")[:12]
    return f"e_{env_id}_v{environment.version}"

def env_root(environment):
    base=Path(settings.PYTHON_ENVIRONMENTS_ROOT).expanduser()
    return base/_short_environment_dir(environment)

def env_python(environment):
    root=env_root(environment)
    return root/("Scripts/python.exe" if os.name=="nt" else "bin/python")

def ensure_environment(environment):
    py=env_python(environment)
    if not py.exists():
        root=env_root(environment)
        root.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run([sys.executable,"-m","venv",str(root)],check=True,capture_output=True,text=True,timeout=180)
    return py

def run_pip(environment,args,timeout=900):
    py=ensure_environment(environment)
    proc=subprocess.run([str(py),"-m","pip",*args],capture_output=True,text=True,timeout=timeout)
    return proc.returncode,(proc.stdout or "")+("\n"+proc.stderr if proc.stderr else "")

def package_health_check(environment, package_name, check_dependencies=True):
    """Validate distribution metadata, importability and dependency consistency."""
    py=ensure_environment(environment); canonical=canonical_package_name(package_name); import_name=import_name_for_package(canonical)
    probe=(
        "import importlib,importlib.metadata,json,sys; "
        "dist=sys.argv[1]; mod=sys.argv[2]; "
        "version=importlib.metadata.version(dist); importlib.import_module(mod); "
        "print(json.dumps({'version':version,'import_name':mod}))"
    )
    proc=subprocess.run([str(py),"-c",probe,canonical,import_name],capture_output=True,text=True,timeout=90)
    if proc.returncode:
        return False,"",(proc.stderr or proc.stdout or "Package import health check failed")[-8000:]
    try: version=json.loads(proc.stdout.strip().splitlines()[-1]).get("version","")
    except Exception: version=""
    if check_dependencies:
        code,check=run_pip(environment,["check"],timeout=120)
        if code:
            return False,version,(check or "pip check failed")[-8000:]
    return True,version,""

def installed_environment_packages(environment):
    """Return pip's actual inventory for the isolated environment."""
    py=ensure_environment(environment)
    proc=subprocess.run([str(py),"-m","pip","list","--format=json"],capture_output=True,text=True,timeout=120)
    if proc.returncode:
        raise RuntimeError((proc.stderr or proc.stdout or "pip list failed")[-4000:])
    return json.loads(proc.stdout or "[]")
