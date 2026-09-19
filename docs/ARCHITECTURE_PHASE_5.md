# Arquitectura — Fase 5

## Objetivo

Construir el View & Binding Engine para que una misma tabla pueda representarse y editarse desde distintas interfaces sin duplicar datos.

## Flujo

```text
TableAsset
   |
   v
ViewDefinition
   |
   +--> ViewFieldBinding
   |
   +--> ViewActionRule
   |
   v
Next.js component
   |
   v
User interaction
   |
   v
Binding translation
   |
   v
Data Records Engine
   |
   v
PostgreSQL writeback
```

## Tipos de vista

- TABLE
- SPREADSHEET
- KANBAN
- MATRIX
- FORM
- CALENDAR

## Principio

Las vistas no almacenan una copia de los registros.

Todas apuntan al mismo `TableAsset`.

Ejemplo:

```text
tasks
 ├── Table View
 ├── Spreadsheet View
 ├── Kanban View
 └── Calendar View
```

Editar cualquiera de ellas modifica la misma fila física.

## Bindings

`ViewFieldBinding` conecta un campo con un rol visual.

Roles:

- DISPLAY
- TITLE
- SUBTITLE
- STATUS
- GROUP
- ROW
- COLUMN
- VALUE
- START_DATE
- END_DATE
- LABEL
- COLOR
- SORT
- HIDDEN

Cada binding define además:
- alias
- editable
- required
- position
- options

## Contratos por vista

Kanban:
- TITLE
- STATUS

Matrix:
- ROW
- COLUMN
- VALUE

Calendar:
- TITLE
- START_DATE

Form:
- al menos un campo editable

TABLE y SPREADSHEET son más flexibles.

## Writeback visual

Ejemplo Kanban:

```text
PENDING
  [Task 125]
       |
       | drag
       v
IN_PROGRESS
```

Interacción:

```json
{
  "action": "MOVE_KANBAN",
  "record_key": "125",
  "expected_version": 4,
  "values": {
    "status": "IN_PROGRESS"
  }
}
```

El binding confirma que `status` es el campo STATUS editable.

Luego se reutiliza el Record Engine de Fase 4:

```text
update_record(...)
```

Por tanto, conserva:
- validación
- transacción
- `__row_version`
- HTTP 409 para conflictos

## Matriz

Ejemplo:

```text
FORECAST(product_id, period, quantity)
```

Bindings:

```text
ROW    -> product_id
COLUMN -> period
VALUE  -> quantity
```

Editar una celda modifica `quantity` del registro correspondiente.

## Calendar

Bindings:

```text
TITLE      -> activity_name
START_DATE -> start_at
END_DATE   -> end_at
```

Una acción `RESIZE_CALENDAR` solo puede modificar los campos vinculados como fecha.

## Separación frontend/backend

El backend devuelve un `schema` de vista.

Next.js decide cómo renderizarlo.

Eso permite cambiar componentes visuales sin modificar la lógica de datos.
