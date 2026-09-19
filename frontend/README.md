# Business Intelligence Frontend — Fase 12

Frontend funcional base para el backend Django/DRF de Business Intelligence Platform.

## Stack

- Next.js App Router
- JavaScript / JSX exclusivamente
- React
- Axios
- CSS global básico

No se utiliza TypeScript.

## Estructura

```text
src/
├── app/          # rutas y páginas
├── components/   # UI, auth y layout
└── lib/          # API, Axios, auth, servicios, hooks y utilidades
```

## Funcionalidad Fase 1

- Registro conectado a `POST /api/v1/auth/register/`
- Login conectado a `POST /api/v1/auth/token/`
- Refresh automático con `POST /api/v1/auth/token/refresh/`
- Usuario actual con `GET /api/v1/auth/me/`
- Logout local
- AuthProvider
- rutas públicas y protegidas
- layout con Sidebar y Topbar
- manejo centralizado de errores de API
- prueba visual de liveness del backend
- navegación preparada para fases siguientes

## Configuración

1. Copiar `.env.example` a `.env.local` si fuera necesario.
2. Verificar:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

3. Backend:

```powershell
python manage.py runserver
```

4. Frontend:

```powershell
npm install
npm run dev
```

5. Abrir:

```text
http://localhost:3000
```

## Nota sobre JWT

La Fase 1 utiliza `localStorage` para access/refresh tokens porque el backend actual expone SimpleJWT directamente y el objetivo inicial es validar lógica y procesos. Para un endurecimiento de seguridad futuro puede migrarse a un patrón BFF con cookies HttpOnly sin cambiar los servicios de dominio.

## Flujo

```text
Login/Register
   ↓
src/lib/services/auth.js
   ↓
src/lib/api/client.js
   ↓
Django /api/v1/auth/*
   ↓
JWT
   ↓
AuthProvider
   ↓
/app protegido
```

## Fase 2 — Organizations + Workspaces

La Fase 2 agrega:

- CRUD funcional de Organizations contra `/api/v1/workspaces/organizations/`.
- CRUD funcional de Workspaces contra `/api/v1/workspaces/`.
- Respeto visual de roles `OWNER`, `ADMIN`, `BUILDER`, `ANALYST`, `VIEWER` conforme al backend.
- `WorkspaceProvider` como contexto global de Organizations, Workspaces y Workspace activo.
- Persistencia del workspace activo en `localStorage`.
- Selector global de workspace en Topbar.
- Páginas `/app/organizations` y `/app/workspaces`.
- Overview actualizado con contexto real de Organization/Workspace.

El backend continúa siendo la autoridad final de permisos; los controles de UI solo evitan acciones que el usuario no debería intentar.

## Fase 3 — Data Sources + Connectors

La Fase 3 agrega:

- CRUD de Data Sources filtrado por workspace activo.
- Modos `MANAGED`, `EXTERNAL` y `PRIVATE_GATEWAY`.
- Motores `PLATFORM_POSTGRES`, `POSTGRESQL`, `SQLSERVER` y `OTHER` según el backend.
- Capacidades lógicas READ / WRITE / DDL.
- Metadatos de conexión no sensibles para fuentes EXTERNAL.
- Credenciales temporales para Connector Layer sin persistir contraseñas.
- Test de conexión PostgreSQL / SQL Server.
- Preview de catálogo con schemas, tablas/vistas, columnas, PK y FK.
- Preview paginado de registros mediante `/connectors/sources/:id/read/`.
- CRUD y filtro de Data Assets.
- `PRIVATE_GATEWAY` preparado para la integración del Customer Data Gateway de la Fase 11.

Las fuentes `MANAGED` no se intentan abrir mediante Connector Layer porque su manipulación corresponde al Data Model Builder/Records de la Fase 4. Las fuentes `PRIVATE_GATEWAY` tampoco usan conexión directa desde el cloud frontend/backend.

## Fase 4 — Data Model Builder + Records

La Fase 4 agrega `/app/data-model` y `/app/records`. El Data Model Builder crea tablas MANAGED mediante `/api/v1/catalog/managed-tables/`, incluyendo campos, PK simples o compuestas, FK simples o compuestas y configuración de tipos soportados por Django. El catálogo muestra TableAsset, FieldAsset y RelationAsset de todas las fuentes del workspace.

Records trabaja exclusivamente sobre tablas MANAGED, como exige el backend. Soporta creación dinámica, listado, filtros `eq/ne/gt/gte/lt/lte/contains`, orden ascendente/descendente, paginación y edición/eliminación con optimistic locking usando `If-Match-Version`. PATCH/DELETE por fila requieren una PK simple según la API actual.

La eliminación física de una tabla MANAGED puede requerir una aprobación previa de Governance. Si Django devuelve `409 requires_approval`, la interfaz informa la dependencia; el flujo de aprobación completo se incorpora en la Fase 11.

## Fase 5 — Views & Binding Engine

Se agregaron Operational Views conectadas al backend `/api/v1/views/`:

- CRUD de `ViewDefinition`.
- Tipos TABLE, SPREADSHEET, KANBAN, MATRIX, FORM y CALENDAR.
- Configuración de `ViewFieldBinding` con roles, aliases, editable/required, posición y options JSON.
- Validación de contratos de vista.
- Configuración de `ViewActionRule` (el backend actual permite crear/listar reglas, pero no expone delete/update dedicado).
- Runtime preview usando `ViewDefinition.schema` + `view.data`.
- Writeback por `/interact/` con `expected_version`, preservando optimistic locking del Records Engine.
- Table: actualización de celdas editables.
- Spreadsheet: edición de celdas con `EDIT_CELL`.
- Kanban: drag & drop entre estados con `MOVE_KANBAN`.
- Matrix: edición del binding VALUE.
- Form: actualización de registros existentes mediante `SUBMIT_FORM`.
- Calendar: reprogramación de START_DATE/END_DATE mediante `RESIZE_CALENDAR`.

### Restricciones reflejadas del backend

El runtime de vistas de Fase 5 reutiliza `data_records.list_records()`, que solo trabaja sobre tablas `MANAGED`. Por ello el frontend solo ofrece tablas MANAGED como fuente de Operational Views funcionales. Además, writeback por registro requiere PK simple y versión de fila.

## Fase 6 — Transformations, Dependencies y Executions

Se añadieron las rutas:

- `/app/transformations`
- `/app/transformations/[id]`
- `/app/dependencies`
- `/app/executions`
- `/app/executions/[id]`

### Transformations

- CRUD de `SQLTransformation`.
- Editor SQL para `SELECT/WITH`.
- Inserción de tokens `{{asset:UUID}}` para Data Assets MANAGED.
- Preview de hasta 500 filas.
- Ejecución asíncrona en queue `sql`.
- Polling de la ejecución iniciada.
- Visualización de output asset e inputs detectados tras ejecutar.

### Dependencies

- Lista y creación de `AssetDependency`.
- Eliminación de edges.
- Selección de `dependency_type` y `refresh_policy`.
- Vista lógica upstream → downstream.
- Lineage directo por Data Asset.
- Asset States y Change Events del workspace.
- La UI evita editar edges existentes: se elimina y recrea el edge para conservar la validación de ciclos del servicio backend.

### Executions

- Lista por workspace.
- Filtros por `status` y `object_type`.
- Polling periódico.
- Detalle de status, progreso, timestamps, queue, task ID, parameters, result y errores.
- Logs por ejecución.
- Solicitud de cancelación para jobs QUEUED/RUNNING.

### Limitaciones reflejadas del backend actual

- SQL Transformation ejecuta directamente solo Data Assets MANAGED del Control Plane PostgreSQL.
- `TransformationInput` no se administra manualmente: se sincroniza al ejecutar a partir de tokens de asset.
- `AUTO` en Dependency Engine marca downstream STALE en `propagate_change`; el backend actual no relanza por sí solo la transformación downstream.
- El endpoint lineage devuelve upstream/downstream directos; la vista global de edges se construye en frontend a partir del listado del workspace.
- La UI limita escritura de dependencias a OWNER/ADMIN/BUILDER. Debe mantenerse la autorización también del lado backend para cualquier operación mutante.


## Fase 8 — Analytics + Charts + Dashboards + Reports

Se agregaron Chart Definitions (KPI, TABLE, BAR, LINE, AREA, PIE, DONUT y SCATTER), dataset runtime, drilldown, Dashboards con Dashboard Items y filtros globales, y Report Definitions con preview del Dashboard asociado. La exportación física de Reports permanece para Fase 11 porque el backend actual no expone todavía un endpoint de render/export de ReportDefinition.

## Fase 9 — Python + Data Science + ML

Se incorporan Python Transformations, Dataset Definitions, ML Model Definitions, training runs, ModelVersions, inferencia batch y PredictionAssets. Las operaciones asíncronas reutilizan el Execution Engine de la Fase 6. Los datasets y Python inputs se limitan en la UI a tablas MANAGED porque el backend actual lee estas fuentes con la conexión PostgreSQL de la plataforma.


## Fase 10 — Optimization Engine

Implementado de forma acumulativa:
- Optimization Models LP/MILP.
- Parámetros fijos, por escenario o derivados de DataAssets MANAGED / artifacts CSV-Parquet compatibles.
- Variables CONTINUOUS, INTEGER y BINARY con bounds numéricos o parametrizados.
- Builder de función objetivo y restricciones lineales.
- SolverConfig para OR-Tools, PuLP y Pyomo.
- Escenarios con overrides de parámetros y baseline de variables.
- Validación de readiness mediante `/optimization/models/{id}/validate/`.
- Ejecución asíncrona mediante Execution Engine y cola `optimization`.
- Historial de OptimizationRun, comparación contra baseline y SolutionAsset/DataAsset para soluciones OPTIMAL/FEASIBLE.

La UI no intenta descargar el artifact JSON de solución porque el backend expone actualmente metadata/artifact_path, no un endpoint de descarga específico en Optimization.

## Fase 11 — Import/Export + Governance + Customer Gateway

Implementado de forma acumulativa:
- Import jobs CSV/XLSX sobre tablas MANAGED con APPEND/UPSERT, column mapping, preview y ejecución asíncrona.
- Export jobs CSV/XLSX con selección de columnas, filtros, row_limit, cuotas y descarga real mediante `/import-export/exports/{id}/download/`.
- Workspace Governance: quota, usage y retention policy.
- Audit Log read-only por workspace.
- Resource Permissions explícitos ALLOW/DENY; el backend actual no expone un directorio de miembros en este módulo, por lo que el formulario usa UUID de usuario.
- DataSource encrypted secrets: estado y escritura/reemplazo; nunca se recuperan credenciales en texto plano.
- Destructive Change Requests con creación, expiración y aprobación; la operación original debe reintentarse después de aprobar.
- Customer Gateway: registro, enrollment code de un solo uso, status ONLINE/OFFLINE/REVOKED, bindings a DataSource PRIVATE_GATEWAY, jobs y documentación de ejecución del agente outbound-only.
- Gateway jobs: TEST_CONNECTION, CATALOG, READ_PAGE, INSERT, UPDATE y DELETE, respetando capacidades can_read/can_write del DataSource.

Limitaciones reflejadas del backend:
- Import/Export directo usa tablas MANAGED del PostgreSQL de la plataforma.
- Import UPSERT requiere PK simple.
- Export filters soportan eq, ne, gt, gte, lt y lte.
- ResourcePermission no dispone todavía de un endpoint de búsqueda/listado de usuarios para construir un selector amigable.
- DestructiveChangeRequest expone approve pero no reject como action dedicada.
- El browser administra gateways, pero el agent token solo existe en el host privado y nunca se devuelve desde endpoints autenticados de administración.

## Fase 12 — Operations + integración completa + validación

La fase final agrega `/app/operations` y cierra el roadmap funcional.

- Liveness público mediante `/api/v1/health/live/`.
- Readiness público mediante `/api/v1/health/ready/`, mostrando checks de database, Redis y artifact storage según la configuración del backend.
- Telemetría privilegiada mediante `/api/v1/ops/status/`: database metrics, Redis, artifact storage, estados globales de executions y gateways.
- El endpoint `/ops/status/` utiliza `IsAdminUser`: requiere `is_staff=True` en Django y no equivale a un rol OWNER/ADMIN de Organization.
- Smoke test transversal del workspace activo contra los endpoints principales de Data, Views, Logic, BI, Data Science, Optimization, Import/Export y Customer Gateway.
- Overview reemplazado por una vista de plataforma completa con navegación a todos los engines.
- Operations se actualiza manualmente y automáticamente cada 30 segundos mientras la vista permanece abierta.

### Validación end-to-end recomendada

```text
Data Source
  → Data Model / Records
  → Operational View / Writeback
  → Change Event / Dependency
  → Transformation / Execution
  → Semantic Model / Metric
  → Chart / Dashboard / Report
  → Python / ML / Prediction
  → Optimization / Solution
  → Import/Export
  → Governance / Gateway
  → Operations
```

La Fase 12 no inventa endpoints de administración adicionales: `WorkspacePlacement` y `OperationalMetricSnapshot` existen en backend pero no tienen API REST pública en `platform_ops/urls.py`, por lo que no se exponen como CRUD en el frontend.
