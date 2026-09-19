# connectors

Capa que abstraerá los motores físicos de datos.

Objetivo futuro:

```text
BaseConnector
├── PostgreSQLConnector
├── SQLServerConnector
└── futuros conectores
```

Los demás engines no deberán conocer credenciales ni detalles físicos del motor.
