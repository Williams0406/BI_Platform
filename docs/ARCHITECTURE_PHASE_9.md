# Arquitectura — Fase 9

## Objetivo

Agregar un Optimization Engine prescriptivo conectado a Data Assets, Dependency Engine y Execution Plane.

```text
Data Assets / ML Predictions
          |
          v
OptimizationParameter
          |
          v
OptimizationScenario
          |
          v
OptimizationModel
  ├── Variables
  ├── Objective
  ├── Constraints
  └── SolverConfig
          |
          v
optimization queue
          |
          v
Solver Adapter
  ├── OR-Tools
  ├── PuLP
  └── Pyomo
          |
          v
OptimizationRun
          |
          +--> Baseline comparison
          |
          v
OptimizationSolutionAsset
          |
          v
DataAsset
```

## Modelo declarativo

La Fase 9 no ejecuta Python arbitrario para construir modelos.

Variables, objetivo y restricciones se almacenan como objetos estructurados.

Ejemplo:

```json
{
  "terms": [
    {"variable": "x", "coefficient": 5},
    {"variable": "y", "coefficient": {"parameter": "unit_profit"}}
  ],
  "constant": 0
}
```

Esto permite compilar el mismo modelo a distintos solvers.

## Problem types

- LP
- MILP

## Variables

Tipos:
- CONTINUOUS
- INTEGER
- BINARY

Los bounds pueden ser escalares:

```json
0
```

o parámetros:

```json
{"parameter": "max_capacity"}
```

## Parameters

Un parámetro puede resolverse desde:

1. `OptimizationScenario.parameter_values`.
2. un DataAsset tabular MANAGED + FieldAsset + agregación.
3. un CSV_ARTIFACT, como PredictionAsset o PythonTransformation output.
4. `default_value`.

Agregaciones escalares:
- SUM
- AVG
- MIN
- MAX
- COUNT

Ejemplo predictive → prescriptive:

```text
PredictionAsset
prediction.csv
      |
      | SUM(prediction)
      v
OptimizationParameter
total_demand
      |
      v
OptimizationModel
```

## Objective

Un modelo tiene un objetivo:
- MINIMIZE
- MAXIMIZE

## Constraints

Cada restricción contiene:
- left_expression
- LE / EQ / GE
- right_value

El RHS puede ser:

```json
150
```

o:

```json
{"parameter": "capacity"}
```

## Solver Adapters

### OR-Tools

Usa `ortools.linear_solver.pywraplp`.

Solver default:
- SCIP

Permite seleccionar otro backend aceptado por OR-Tools mediante `solver_name`.

### PuLP

Implementación inicial:
- `PULP_CBC_CMD`

Soporta:
- time limit
- relative MIP gap
- threads

### Pyomo

Construye un `ConcreteModel` y usa `SolverFactory`.

Pyomo es la capa de modelado; un solver externo compatible debe existir en el entorno.

Ejemplos:
- highs
- glpk
- cbc

Si el executable/solver no está disponible, la corrida falla claramente en lugar de hacer fallback silencioso.

## SolverConfig

```text
adapter
solver_name
time_limit_seconds
mip_gap
threads
options
is_default
```

## Scenario

Permite comparar supuestos sin duplicar el modelo:

```text
Scenario A
capacity = 1000
demand = 850

Scenario B
capacity = 1200
demand = 1100
```

También puede almacenar un baseline operacional:

```json
{
  "x": 30,
  "y": 40
}
```

## Baseline

Antes o después de resolver se calcula:

- factibilidad del baseline
- objective baseline
- violations
- improvement_absolute
- improvement_percent

Para MINIMIZE:

```text
improvement = baseline - optimized
```

Para MAXIMIZE:

```text
improvement = optimized - baseline
```

Un baseline infactible se reporta, pero no se usa para calcular mejora económica porcentual.

## OptimizationRun

Separa el estado matemático del estado técnico.

Execution puede terminar `SUCCESS` si el solver funcionó correctamente aunque el modelo resulte `INFEASIBLE`.

OptimizationRun:
- QUEUED
- RUNNING
- OPTIMAL
- FEASIBLE
- INFEASIBLE
- UNBOUNDED
- FAILED
- CANCELLED

Guarda:
- objective
- best bound
- gap
- solve time
- variable values
- input asset versions
- solver metadata
- baseline metrics

## Solution Assets

Para una solución factible/óptima se crea:

```text
runtime_artifacts/
└── optimization/
    └── <model-id>/
        └── <run-id>/
            └── solution.json
```

y se registra:
- OptimizationSolutionAsset
- DataAsset DATASET

Esto permite que BI, Transformations u otros modelos consuman resultados de optimización.

En Fase 12 los artifacts migrarán naturalmente a Object Storage.

## Dependency DAG

Entradas:

```text
Data Asset input
      ↓
Optimization Model
```

Solución:

```text
Optimization Model + Data Inputs
              ↓
       Solution DataAsset
```

Si cambian inputs vinculados a parámetros, el Optimization Model puede quedar STALE.

## Queue

Nueva cola:

```text
optimization
```

Se mantiene separada de:
- fast
- sql
- python
- ml

para evitar que MILP/LP de larga duración bloquee otros workloads.
