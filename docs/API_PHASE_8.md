# API — Fase 8

## Python Transformations

```http
GET  /api/v1/data-science/python-transformations/
POST /api/v1/data-science/python-transformations/
```

Ejemplo:

```json
{
  "workspace": "<uuid>",
  "name": "Customer Summary",
  "output_name": "customer_summary_python",
  "code": "df = table('orders')\nresult = df.groupby('customer_id', as_index=False)['total'].sum()\nsave_table(result)",
  "allowed_packages": ["pandas"],
  "timeout_seconds": 120,
  "memory_limit_mb": 512,
  "max_input_rows": 50000
}
```

Input:

```http
POST /api/v1/data-science/python-transformations/{id}/inputs/
```

Run:

```http
POST /api/v1/data-science/python-transformations/{id}/run/
```

## Datasets

```http
GET  /api/v1/data-science/datasets/
POST /api/v1/data-science/datasets/
```

## Models

```http
GET  /api/v1/data-science/models/
POST /api/v1/data-science/models/
```

Ejemplo:

```json
{
  "workspace": "<uuid>",
  "dataset": "<dataset-uuid>",
  "name": "Demand Forecast Baseline",
  "task_type": "REGRESSION",
  "algorithm": "RANDOM_FOREST_REGRESSOR",
  "features": ["<field-a>", "<field-b>"],
  "target": "<target-field>",
  "parameters": {
    "n_estimators": 300,
    "max_depth": 12
  },
  "test_size": 0.2,
  "random_state": 42
}
```

Training:

```http
POST /api/v1/data-science/models/{id}/train/
```

## Runs

```http
GET /api/v1/data-science/runs/
GET /api/v1/data-science/runs/?model=<uuid>
```

## Versions

```http
GET /api/v1/data-science/versions/
GET /api/v1/data-science/versions/?model=<uuid>
```

## Batch inference

```http
POST /api/v1/data-science/versions/{version_id}/infer/
```

```json
{
  "dataset": "<dataset-uuid>"
}
```

## Predictions

```http
GET /api/v1/data-science/predictions/
```
