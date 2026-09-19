# Arquitectura — Fase 7

## Objetivo

Construir la capa BI sobre los Data Assets y el Execution/Dependency Engine.

## Arquitectura

```text
TableAsset / DataAsset
        |
        v
SemanticModel
        |
        +--> SemanticDimension
        |
        +--> MetricDefinition
                 |
                 v
           Metric Query Engine
                 |
                 v
          ChartDefinition
                 |
                 v
       DashboardDefinition
                 |
                 v
          ReportDefinition
```

## Semantic Model

Representa una vista de negocio sobre una tabla base.

Ejemplo:

```text
TableAsset: ws_x.orders
        ↓
SemanticModel: Ventas
```

## Dimensions

Ejemplos:
- Cliente
- Producto
- Estado
- Fecha
- Región

Cada dimensión referencia un `FieldAsset`.

Tipos:
- CATEGORY
- DATE
- DATETIME
- NUMBER
- TEXT

Puede almacenar `hierarchy`, por ejemplo:

```json
["year", "quarter", "month", "day"]
```

## Metrics

Una métrica puede ser:

### SIMPLE
- SUM
- AVG
- MIN
- MAX
- COUNT
- COUNT_DISTINCT

### SQL
Una expresión controlada, no una sentencia SQL completa.

Ejemplo:

```text
SUM({{field:revenue}} - {{field:cost}})
```

El backend resuelve los tokens a identificadores SQL seguros.

## Metric Data Asset

Cada métrica se registra también como `DataAsset` tipo METRIC.

Esto permite que más adelante:
- dashboards
- reports
- dependencies
- alerts
- ML
- optimization

puedan depender de ella como cualquier otro asset.

## Metric Query Engine

Entrada:

```text
Metric + Dimensions + Filters
```

Salida:

```text
Dataset
```

Ejemplo:

```text
Revenue
GROUP BY Region
FILTER Year = 2026
```

## Cache

Cada métrica define:

```text
cache_ttl_seconds
```

La consulta puede usar el Django cache backend.

## Charts

Tipos iniciales:
- KPI
- TABLE
- BAR
- LINE
- AREA
- PIE
- DONUT
- SCATTER

Un Chart no guarda datos: guarda la definición de consulta y visualización.

## Dashboard

Contiene:
- layout
- global_filters
- DashboardItems

Cada item referencia un Chart y puede tener:
- position
- title_override
- config_override

## Global Filters

Los filtros del dashboard se combinan con:
- filtros por defecto del chart
- filtros runtime enviados por Next.js

## Drill-down

Se realiza usando el orden de dimensiones del Chart.

Ejemplo:

```text
Año
 ↓
Mes
 ↓
Día
```

El endpoint recibe `drill_level`.

## Reports

ReportDefinition referencia opcionalmente un Dashboard.

En Fase 7 se define el objeto y configuración.
La generación real PDF/XLSX/CSV se integrará con Import/Export y workers posteriores.

## Frontend

Next.js no necesita construir SQL.

Solicita datasets:

```text
Chart.dataset()
Dashboard.dataset()
Metric.query()
```

Eso mantiene una única definición de negocio en backend.
