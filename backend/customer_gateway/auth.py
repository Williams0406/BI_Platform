import hashlib,hmac,secrets
from dataclasses import dataclass
from django.utils import timezone
from .models import GatewayRegistration

def hash_token(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def generate_secret(bytes_count=32):
    return secrets.token_urlsafe(bytes_count)

def verify_secret(raw,hashed):
    return bool(raw and hashed and hmac.compare_digest(hash_token(raw),hashed))

def extract_bearer(request):
    header=request.META.get("HTTP_AUTHORIZATION","")
    if not header.lower().startswith("bearer "):
        return ""
    return header.split(" ",1)[1].strip()

def authenticate_gateway_request(request):
    raw=extract_bearer(request)
    if not raw:return None
    token_hash=hash_token(raw)
    gateway=GatewayRegistration.objects.filter(agent_token_hash=token_hash).first()
    if not gateway or gateway.status==GatewayRegistration.Status.REVOKED:return None
    return gateway
