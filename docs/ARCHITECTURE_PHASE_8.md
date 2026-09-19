# Arquitectura — Fase 8

## Objetivo

Agregar Python Runtime controlado y ciclo de vida de Data Science:

```text
Data Assets / TableAssets
        |
        +-----------------------+
        |                       |
        v                       v
PythonTransformation      DatasetDefinition
        |                       |
        v                       v
python queue              ModelDefinition
        |                       |
        v                       v
Subprocess Runtime          ml queue
        |                       |
        v                       v
CSV DataAsset             Training
                                |
                                v
                           ModelRun
                                |
                                v
                          ModelVersion
                                |
                                v
                         Batch Inference
                                |
                                v
                       Prediction DataAsset
```

## Python Runtime

El código de usuario no se ejecuta dentro del proceso Django.

Flujo:

```text
Django → Execution → Celery python queue → subprocess → temp directory
```

API del script:

```python
orders = table("orders")
result = orders.groupby("customer_id", as_index=False)["total"].sum()
save_table(result)
```

El subprocess recibe datasets temporales, no credenciales de base de datos ni settings Django.

### Controles

- `python -I`
- subprocess separado
- entorno mínimo
- directorio temporal
- timeout
- whitelist de imports
- límite máximo de filas
- límite de memoria con `resource` en Unix
- sin Docker

**Importante:** esto es defensa en profundidad, no una frontera de sandbox fuerte para código deliberadamente hostil. En producción el Python Worker debe ejecutarse en cuenta/host/VM aislado, con restricciones de red y filesystem.

En Windows el timeout funciona, pero `resource.RLIMIT_AS` no está disponible.

## Output Python

El resultado se persiste inicialmente como:

```text
runtime_artifacts/python_outputs/<transformation>/latest.csv
```

y se registra como `DataAsset` tipo `DATASET`.

Object Storage se incorporará en la Fase 12.

## DatasetDefinition

Define una fuente tabular reutilizable para ML:
- source_table
- filter_config
- sample_limit
- enabled

## ModelDefinition

Define:
- Dataset
- task type
- algorithm
- features
- target
- parameters
- test_size
- random_state

Algoritmos iniciales:

Classification:
- Logistic Regression
- Random Forest Classifier

Regression:
- Linear Regression
- Random Forest Regressor

## Pipeline

Los modelos usan `sklearn.pipeline.Pipeline`.

Numéricos:
- imputación por mediana

Categóricos:
- imputación most_frequent
- OneHotEncoder(handle_unknown="ignore")

El preprocessing y el estimator se versionan juntos.

## Training

```text
Dataset
 → Features / Target
 → train_test_split
 → Pipeline.fit
 → Evaluation
 → joblib artifact
 → ModelVersion
```

Métricas:

Classification:
- accuracy
- F1 weighted

Regression:
- MAE
- MSE
- RMSE
- R²

## Reproducibilidad

`ModelRun` registra:
- snapshot de parámetros
- versión del DataAsset de entrenamiento
- número de filas
- filas train/test
- métricas
- timestamps
- Execution asociada

## Versioning

Cada entrenamiento exitoso crea:

```text
ModelVersion v1
ModelVersion v2
...
```

Incluye:
- artifact_path
- métricas
- features
- target
- algoritmo
- versión scikit-learn

## Batch inference

Una versión concreta puede inferir sobre otro Dataset compatible.

Output:

```text
ModelVersion + Dataset
        ↓
Prediction CSV
        ↓
PredictionAsset
        ↓
DataAsset DATASET
```

Esto permite encadenar posteriormente predicciones con Metrics, Analytics y Optimization.

## Dependency DAG

Después del primer entrenamiento exitoso:

```text
Training Table → ML Model DataAsset
```

y después de inferencia:

```text
ML Model + Inference Dataset → Prediction DataAsset
```

Si cambian los datos de entrenamiento, el Dependency Engine puede marcar el modelo como `STALE`.
