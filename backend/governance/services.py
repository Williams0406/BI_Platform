import json
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from execution.models import Execution
from .models import AuditLog, EncryptedSecret, ResourcePermission, WorkspaceQuota, WorkspaceUsage

class GovernanceError(ValueError): pass
class QuotaExceeded(GovernanceError): pass

def audit(workspace, action, resource_type, resource_id="", actor=None, detail=None, ip_address=None):
    return AuditLog.objects.create(
        workspace=workspace, actor=actor, action=action, resource_type=resource_type,
        resource_id=str(resource_id or ""), detail=detail or {}, ip_address=ip_address,
    )

def get_quota(workspace):
    quota,_=WorkspaceQuota.objects.get_or_create(workspace=workspace)
    return quota

def get_usage(workspace):
    usage,_=WorkspaceUsage.objects.get_or_create(workspace=workspace)
    return usage

def assert_can_start_job(workspace):
    quota=get_quota(workspace)
    active=Execution.objects.filter(workspace=workspace,status__in=[Execution.Status.QUEUED,Execution.Status.RUNNING]).count()
    if active >= quota.max_concurrent_jobs:
        raise QuotaExceeded(f"Se alcanzó el máximo de {quota.max_concurrent_jobs} jobs concurrentes.")

def assert_import_rows(workspace, rows):
    if rows > get_quota(workspace).max_import_rows:
        raise QuotaExceeded("La importación supera max_import_rows.")

def assert_export_rows(workspace, rows):
    if rows > get_quota(workspace).max_export_rows:
        raise QuotaExceeded("La exportación supera max_export_rows.")

def add_usage(workspace, *, storage_bytes=0, import_rows=0, export_rows=0, executions=0):
    usage=get_usage(workspace)
    usage.storage_bytes += max(0,int(storage_bytes))
    usage.import_rows += max(0,int(import_rows))
    usage.export_rows += max(0,int(export_rows))
    usage.executions_started += max(0,int(executions))
    usage.save()
    return usage

def _fernet():
    key=settings.GOVERNANCE_FERNET_KEY
    if not key:
        raise GovernanceError("GOVERNANCE_FERNET_KEY no está configurada.")
    try:
        return Fernet(key.encode() if isinstance(key,str) else key)
    except Exception as exc:
        raise GovernanceError("GOVERNANCE_FERNET_KEY no es una clave Fernet válida.") from exc

def encrypt_secret_payload(payload):
    raw=json.dumps(payload,ensure_ascii=False).encode("utf-8")
    return _fernet().encrypt(raw)

def decrypt_secret_payload(secret):
    try:
        raw=_fernet().decrypt(bytes(secret.ciphertext))
        return json.loads(raw.decode("utf-8"))
    except InvalidToken as exc:
        raise GovernanceError("No se pudo descifrar el secreto.") from exc

def save_datasource_secret(data_source, payload, user):
    secret,_=EncryptedSecret.objects.update_or_create(
        data_source=data_source,
        defaults={
            "workspace":data_source.workspace,
            "name":f"datasource:{data_source.id}",
            "ciphertext":encrypt_secret_payload(payload),
            "created_by":user,
        },
    )
    return secret

def has_resource_permission(user, workspace, resource_type, action, resource_id="", field_name=""):
    rules=ResourcePermission.objects.filter(
        workspace=workspace,user=user,resource_type=resource_type,action=action
    ).filter(Q(resource_id="")|Q(resource_id=str(resource_id or ""))).filter(Q(field_name="")|Q(field_name=field_name))
    if rules.filter(effect=ResourcePermission.Effect.DENY).exists():
        return False
    if rules.filter(effect=ResourcePermission.Effect.ALLOW).exists():
        return True
    return None


def require_approved_destructive_change(workspace, action, resource_type, resource_id):
    from .models import DestructiveChangeRequest
    now=timezone.now()
    request=DestructiveChangeRequest.objects.filter(
        workspace=workspace,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        status=DestructiveChangeRequest.Status.APPROVED,
    ).order_by("-approved_at").first()
    if not request:
        raise GovernanceError("La operación destructiva requiere aprobación previa.")
    if request.expires_at and request.expires_at < now:
        request.status=DestructiveChangeRequest.Status.EXPIRED
        request.save(update_fields=["status"])
        raise GovernanceError("La aprobación destructiva expiró.")
    return request

def mark_destructive_executed(request, actor=None):
    from .models import DestructiveChangeRequest
    request.status=DestructiveChangeRequest.Status.EXECUTED
    request.executed_at=timezone.now()
    request.save(update_fields=["status","executed_at"])
    audit(
        request.workspace,
        "DESTRUCTIVE_EXECUTED",
        request.resource_type,
        request.resource_id,
        actor,
        {"request_id":str(request.id),"action":request.action},
    )
