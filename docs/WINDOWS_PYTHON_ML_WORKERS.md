# Python + ML workers en Windows — sin Docker

Con Redis operativo:

```powershell
celery -A config worker -l INFO -Q python --pool=solo
```

```powershell
celery -A config worker -l INFO -Q ml --pool=solo
```

El Python Worker lanza un subprocess separado por ejecución.

Para producción, separar:
- Django web
- worker Python
- worker ML

preferiblemente mediante cuentas de sistema o hosts/VM diferentes, incluso sin Docker.
