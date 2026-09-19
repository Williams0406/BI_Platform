# API — Fase 9

## Models

```http
GET  /api/v1/optimization/models/
POST /api/v1/optimization/models/
```

Ejemplo:

```json
{
  "workspace": "<uuid>",
  "name": "Production Mix",
  "problem_type": "MILP"
}
```

Validar definición:

```http
GET /api/v1/optimization/models/{id}/validate/
```

## Parameters

```http
POST /api/v1/optimization/parameters/
```

Manual/default:

```json
{
  "model": "<uuid>",
  "name": "capacity",
  "value_type": "NUMBER",
  "default_value": 1000
}
```

Desde PredictionAsset CSV:

```json
{
  "model": "<uuid>",
  "name": "forecast_demand",
  "value_type": "NUMBER",
  "source_asset": "<prediction-data-asset-uuid>",
  "source_column": "prediction",
  "source_aggregation": "SUM"
}
```

## Variables

```http
POST /api/v1/optimization/variables/
```

```json
{
  "model": "<uuid>",
  "name": "production_a",
  "variable_type": "INTEGER",
  "lower_bound": 0,
  "upper_bound": {"parameter": "capacity"}
}
```

## Objective

```http
POST /api/v1/optimization/objectives/
```

```json
{
  "model": "<uuid>",
  "name": "Profit",
  "sense": "MAXIMIZE",
  "expression": {
    "constant": 0,
    "terms": [
      {"variable": "production_a", "coefficient": 15},
      {"variable": "production_b", "coefficient": 12}
    ]
  }
}
```

## Constraints

```http
POST /api/v1/optimization/constraints/
```

```json
{
  "model": "<uuid>",
  "name": "Machine hours",
  "left_expression": {
    "terms": [
      {"variable": "production_a", "coefficient": 2},
      {"variable": "production_b", "coefficient": 1}
    ]
  },
  "sense": "LE",
  "right_value": {"parameter": "capacity"}
}
```

## Solver config

```http
POST /api/v1/optimization/solver-configs/
```

OR-Tools:

```json
{
  "model": "<uuid>",
  "name": "OR Tools SCIP",
  "adapter": "ORTOOLS",
  "solver_name": "SCIP",
  "time_limit_seconds": 300,
  "mip_gap": 0.01,
  "threads": 4,
  "is_default": true
}
```

PuLP:

```json
{
  "model": "<uuid>",
  "name": "CBC",
  "adapter": "PULP",
  "solver_name": "PULP_CBC_CMD",
  "time_limit_seconds": 300
}
```

Pyomo:

```json
{
  "model": "<uuid>",
  "name": "Pyomo HiGHS",
  "adapter": "PYOMO",
  "solver_name": "highs",
  "time_limit_seconds": 300
}
```

Pyomo requiere que el solver elegido esté instalado/disponible.

## Scenarios

```http
POST /api/v1/optimization/scenarios/
```

```json
{
  "model": "<uuid>",
  "name": "High Demand",
  "parameter_values": {
    "capacity": 1200
  },
  "baseline_values": {
    "production_a": 300,
    "production_b": 400
  }
}
```

## Run

```http
POST /api/v1/optimization/models/{id}/run/
```

```json
{
  "scenario": "<scenario-uuid>",
  "solver_config": "<solver-config-uuid>"
}
```

`solver_config` puede omitirse si existe uno default.

Respuesta:

```json
{
  "optimization_run_id": "...",
  "execution_id": "...",
  "solver": "ORTOOLS",
  "status": "QUEUED"
}
```

## Runs

```http
GET /api/v1/optimization/runs/
GET /api/v1/optimization/runs/?model=<uuid>
GET /api/v1/optimization/runs/?status=OPTIMAL
```

## Solutions

```http
GET /api/v1/optimization/solutions/
```
