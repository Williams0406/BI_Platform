# Import/Export Worker en Windows — sin Docker

Con Redis:

```powershell
celery -A config worker -l INFO -Q imports --pool=solo
```

Para seguridad de secretos genere una clave Fernet fuera del código:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copie el resultado a `.env`:

```text
GOVERNANCE_FERNET_KEY=<clave>
```

No suba esa clave al repositorio.

Los archivos se guardan inicialmente bajo `backend/media/`.
En Fase 12 se migrarán a Object Storage.
