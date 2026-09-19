from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from datasources.models import DataSource
from governance.services import audit
from .auth import generate_secret,hash_token,verify_secret
from .models import GatewayDataSourceBinding,GatewayHeartbeat,GatewayJob,GatewayRegistration

def create_gateway(workspace,name,user):
    code=generate_secret(12)
    gateway=GatewayRegistration.objects.create(
        workspace=workspace,name=name,created_by=user,
        enrollment_code_hash=hash_token(code),
        enrollment_expires_at=timezone.now()+timedelta(minutes=settings.GATEWAY_ENROLLMENT_TTL_MINUTES),
    )
    audit(workspace,"GATEWAY_CREATE","GatewayRegistration",gateway.id,user)
    return gateway,code

@transaction.atomic
def enroll_gateway(gateway_id,enrollment_code,metadata=None,ip_address=None):
    gateway=GatewayRegistration.objects.select_for_update().filter(id=gateway_id).first()
    if not gateway:raise ValueError("Gateway no encontrado.")
    if gateway.status==GatewayRegistration.Status.REVOKED:raise ValueError("Gateway revocado.")
    if not gateway.enrollment_expires_at or gateway.enrollment_expires_at<timezone.now():
        raise ValueError("Código de enrollment expirado.")
    if not verify_secret(enrollment_code,gateway.enrollment_code_hash):
        raise ValueError("Código de enrollment inválido.")
    token=generate_secret(32)
    metadata=metadata or {}
    gateway.agent_token_hash=hash_token(token);gateway.token_version+=1
    gateway.enrollment_code_hash="";gateway.enrollment_expires_at=None
    gateway.status=GatewayRegistration.Status.ONLINE;gateway.last_seen_at=timezone.now()
    gateway.agent_version=metadata.get("agent_version","")
    gateway.platform=metadata.get("platform","")
    gateway.hostname=metadata.get("hostname","")
    gateway.capabilities=metadata.get("capabilities",{})
    gateway.last_ip=ip_address
    gateway.save()
    audit(gateway.workspace,"GATEWAY_ENROLL","GatewayRegistration",gateway.id,None,{"token_version":gateway.token_version},ip_address)
    return gateway,token

@transaction.atomic
def rotate_agent_token(gateway,ip_address=None):
    token=generate_secret(32)
    gateway.agent_token_hash=hash_token(token);gateway.token_version+=1;gateway.last_seen_at=timezone.now();gateway.last_ip=ip_address
    gateway.save(update_fields=["agent_token_hash","token_version","last_seen_at","last_ip","updated_at"])
    audit(gateway.workspace,"GATEWAY_TOKEN_ROTATE","GatewayRegistration",gateway.id,None,{"token_version":gateway.token_version},ip_address)
    return token

def heartbeat(gateway,metadata=None,ip_address=None):
    metadata=metadata or {}
    gateway.status=GatewayRegistration.Status.ONLINE
    gateway.last_seen_at=timezone.now()
    gateway.last_ip=ip_address
    gateway.agent_version=metadata.get("agent_version",gateway.agent_version)
    gateway.platform=metadata.get("platform",gateway.platform)
    gateway.hostname=metadata.get("hostname",gateway.hostname)
    gateway.capabilities=metadata.get("capabilities",gateway.capabilities)
    gateway.save(update_fields=["status","last_seen_at","last_ip","agent_version","platform","hostname","capabilities","updated_at"])
    GatewayHeartbeat.objects.create(gateway=gateway,agent_version=gateway.agent_version,metrics=metadata.get("metrics",{}))
    return gateway

def refresh_online_status(gateway):
    if gateway.status in {GatewayRegistration.Status.REVOKED,GatewayRegistration.Status.PENDING}:return gateway.status
    cutoff=timezone.now()-timedelta(seconds=settings.GATEWAY_OFFLINE_AFTER_SECONDS)
    status=GatewayRegistration.Status.ONLINE if gateway.last_seen_at and gateway.last_seen_at>=cutoff else GatewayRegistration.Status.OFFLINE
    if gateway.status!=status:
        gateway.status=status;gateway.save(update_fields=["status","updated_at"])
    return status

def bind_datasource(gateway,data_source,local_connection_name):
    if data_source.workspace_id!=gateway.workspace_id:raise ValueError("Gateway y DataSource deben pertenecer al mismo workspace.")
    if data_source.mode!=DataSource.Mode.PRIVATE_GATEWAY:raise ValueError("El DataSource debe usar mode PRIVATE_GATEWAY.")
    binding,_=GatewayDataSourceBinding.objects.update_or_create(
        data_source=data_source,
        defaults={"gateway":gateway,"local_connection_name":local_connection_name,"enabled":True},
    )
    audit(gateway.workspace,"GATEWAY_BIND","DataSource",data_source.id,gateway.created_by,{"gateway_id":str(gateway.id),"local_connection_name":local_connection_name})
    return binding

def queue_job(data_source,operation,payload,user=None):
    if data_source.mode!=DataSource.Mode.PRIVATE_GATEWAY:raise ValueError("DataSource no es PRIVATE_GATEWAY.")
    try:binding=data_source.gateway_binding
    except Exception as exc:raise ValueError("DataSource no tiene Gateway binding.") from exc
    if not binding.enabled:raise ValueError("Gateway binding deshabilitado.")
    job=GatewayJob.objects.create(gateway=binding.gateway,data_source=data_source,operation=operation,payload=payload or {},requested_by=user)
    audit(data_source.workspace,"GATEWAY_JOB_QUEUE","GatewayJob",job.id,user,{"operation":operation,"data_source":str(data_source.id)})
    return job

@transaction.atomic
def claim_next_job(gateway):
    now=timezone.now()
    GatewayJob.objects.filter(
        gateway=gateway,status=GatewayJob.Status.CLAIMED,lease_expires_at__lt=now
    ).update(status=GatewayJob.Status.QUEUED,claimed_at=None,lease_expires_at=None)
    job=GatewayJob.objects.select_for_update(skip_locked=True).filter(gateway=gateway,status=GatewayJob.Status.QUEUED).order_by("created_at").first()
    if not job:return None
    job.status=GatewayJob.Status.CLAIMED;job.claimed_at=now;job.lease_expires_at=now+timedelta(seconds=settings.GATEWAY_JOB_LEASE_SECONDS);job.save(update_fields=["status","claimed_at","lease_expires_at"])
    binding=job.data_source.gateway_binding
    return job,binding.local_connection_name

def complete_job(gateway,job_id,success,result=None,error_message=""):
    job=GatewayJob.objects.filter(id=job_id,gateway=gateway,status=GatewayJob.Status.CLAIMED).select_related("data_source","requested_by").first()
    if not job:raise ValueError("Job no encontrado o no reclamado.")
    job.status=GatewayJob.Status.SUCCESS if success else GatewayJob.Status.FAILED
    job.result=result or {};job.error_message=error_message or "";job.finished_at=timezone.now();job.lease_expires_at=None;job.save(update_fields=["status","result","error_message","finished_at","lease_expires_at"])
    audit(job.data_source.workspace,"GATEWAY_JOB_SUCCESS" if success else "GATEWAY_JOB_FAILED","GatewayJob",job.id,job.requested_by,{"operation":job.operation,"error":job.error_message})
    return job

@transaction.atomic
def renew_enrollment(gateway,user=None):
    code=generate_secret(12)
    gateway.enrollment_code_hash=hash_token(code)
    gateway.enrollment_expires_at=timezone.now()+timedelta(minutes=settings.GATEWAY_ENROLLMENT_TTL_MINUTES)
    gateway.agent_token_hash=""
    gateway.status=GatewayRegistration.Status.PENDING
    gateway.save(update_fields=["enrollment_code_hash","enrollment_expires_at","agent_token_hash","status","updated_at"])
    audit(gateway.workspace,"GATEWAY_REPAIR","GatewayRegistration",gateway.id,user)
    return code
