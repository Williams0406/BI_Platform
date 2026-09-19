# API — Fase 7

## Semantic Models

```http
GET    /api/v1/metrics/semantic-models/
POST   /api/v1/metrics/semantic-models/
GET    /api/v1/metrics/semantic-models/{id}/
PATCH  /api/v1/metrics/semantic-models/{id}/
DELETE /api/v1/metrics/semantic-models/{id}/
```

## Dimensions

```http
GET  /api/v1/metrics/dimensions/
POST /api/v1/metrics/dimensions/
```

Ejemplo:

```json
{
  "semantic_model": "<uuid>",
  "field": "<field-uuid>",
  "name": "Región",
  "dimension_type": "CATEGORY",
  "sort_order": 1
}
```

## Metrics

```http
GET    /api/v1/metrics/
POST   /api/v1/metrics/
GET    /api/v1/metrics/{id}/
PATCH  /api/v1/metrics/{id}/
DELETE /api/v1/metrics/{id}/
```

Ejemplo SIMPLE:

```json
{
  "workspace": "<uuid>",
  "semantic_model": "<uuid>",
  "name": "Revenue",
  "expression_type": "SIMPLE",
  "source_field": "<field-total-uuid>",
  "aggregation": "SUM",
  "format_type": "CURRENCY",
  "unit": "PEN",
  "decimal_places": 2
}
```

## Query metric

```http
POST /api/v1/metrics/{id}/query/
```

```json
{
  "dimensions": ["<dimension-uuid>"],
  "filters": [
    {
      "field": "status",
      "operator": "eq",
      "value": "PAID"
    }
  ],
  "limit": 1000,
  "use_cache": true
}
```

## Charts

```http
GET  /api/v1/analytics/charts/
POST /api/v1/analytics/charts/
```

```json
{
  "workspace": "<uuid>",
  "name": "Ventas por región",
  "chart_type": "BAR",
  "metric": "<metric-uuid>",
  "dimensions": ["<region-dimension-uuid>"],
  "config": {
    "orientation": "vertical"
  }
}
```

Dataset:

```http
POST /api/v1/analytics/charts/{id}/dataset/
```

Drill-down:

```http
POST /api/v1/analytics/charts/{id}/drilldown/
```

```json
{
  "drill_level": 2,
  "filters": []
}
```

## Dashboards

```http
GET  /api/v1/analytics/dashboards/
POST /api/v1/analytics/dashboards/
```

Items:

```http
GET  /api/v1/analytics/dashboard-items/
POST /api/v1/analytics/dashboard-items/
```

Dashboard dataset:

```http
POST /api/v1/analytics/dashboards/{id}/dataset/
```

## Reports

```http
GET  /api/v1/analytics/reports/
POST /api/v1/analytics/reports/
```
