# Optimization Worker en Windows — sin Docker

Con Redis operativo:

```powershell
celery -A config worker -l INFO -Q optimization --pool=solo
```

## OR-Tools

OR-Tools incluye wheels para Windows y Python moderno.

El adapter usa MPSolver y por defecto intenta:

```text
SCIP
```

Puede configurarse otro backend soportado mediante `solver_name`.

## PuLP

El adapter inicial usa:

```text
PULP_CBC_CMD
```

## Pyomo

Pyomo no implica automáticamente que un solver executable esté instalado.

Si usa:

```json
{
  "adapter": "PYOMO",
  "solver_name": "highs"
}
```

el entorno debe disponer de ese solver.

Para desarrollo puede preferirse OR-Tools o PuLP por requerir menos configuración externa.

## Producción

Mantener un worker `optimization` separado permite:
- límites de concurrencia específicos
- timeouts
- control de RAM/CPU
- evitar bloqueo de ML/SQL/API
