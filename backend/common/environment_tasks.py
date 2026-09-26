from celery import shared_task
from .models import EnvironmentPackage
from .environment_services import canonical_package_name, package_health_check, run_pip

@shared_task(name="common.environment_tasks.install_environment_package")
def install_environment_package(package_id):
    p=EnvironmentPackage.objects.select_related("environment").get(pk=package_id)
    canonical=canonical_package_name(p.name)
    if p.name != canonical: p.name=canonical
    p.status="INSTALLING"; p.log=""; p.installed_version=""
    p.save(update_fields=["name","status","log","installed_version","updated_at"])
    spec=p.name + (p.version_spec if p.version_spec and p.version_spec[0] in "<>=!~" else ("=="+p.version_spec if p.version_spec else ""))
    try:
        code,log=run_pip(p.environment,["install","--no-cache-dir",spec])
        # A damaged previous install may have missing RECORD metadata. Repair it
        # without asking pip to uninstall the broken distribution first.
        if code and ("no RECORD file" in log or "uninstall-no-record-file" in log):
            repair=["install","--ignore-installed","--no-cache-dir",spec]
            code,repair_log=run_pip(p.environment,repair)
            log += "\n\n--- automatic repair ---\n" + repair_log
        p.log=log[-20000:]
        if code:
            p.status="FAILED"
        else:
            healthy,version,health_log=package_health_check(p.environment,p.name)
            p.installed_version=version
            if healthy:
                p.status="INSTALLED"
            else:
                p.status="FAILED"
                p.log=(p.log+"\n\n--- health check failed ---\n"+health_log)[-20000:]
    except Exception as exc:
        p.status="FAILED"; p.log=str(exc)
    p.save(update_fields=["status","log","installed_version","updated_at"])
    return {"id":str(p.id),"status":p.status,"version":p.installed_version}

@shared_task(name="common.environment_tasks.uninstall_environment_package")
def uninstall_environment_package(package_id):
    try: p=EnvironmentPackage.objects.select_related("environment").get(pk=package_id)
    except EnvironmentPackage.DoesNotExist: return {"deleted":True}
    p.status="UNINSTALLING"; p.save(update_fields=["status","updated_at"])
    try:
        code,log=run_pip(p.environment,["uninstall","-y",canonical_package_name(p.name)],timeout=300)
        if code:
            p.status="FAILED"; p.log=log[-20000:]; p.save(update_fields=["status","log","updated_at"]); return {"deleted":False,"status":"FAILED"}
        p.delete(); return {"deleted":True}
    except Exception as exc:
        p.status="FAILED"; p.log=str(exc); p.save(update_fields=["status","log","updated_at"]); return {"deleted":False,"status":"FAILED"}
