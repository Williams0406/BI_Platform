# SQL Server Connector en Windows

Además de:

```powershell
pip install -r requirements.txt
```

el equipo debe tener instalado un Microsoft ODBC Driver for SQL Server.

El connector utiliza por defecto:

```text
ODBC Driver 18 for SQL Server
```

Ejemplo de metadata para autenticación SQL:

```json
{
  "server": "SERVIDOR01\\\\SQLEXPRESS",
  "database": "ERP",
  "user": "bi_reader",
  "driver": "ODBC Driver 18 for SQL Server",
  "encrypt": true,
  "trust_server_certificate": true
}
```

El `password` se envía solo al endpoint de ejecución.

Ejemplo con Windows Authentication:

```json
{
  "server": "SERVIDOR01\\\\SQLEXPRESS",
  "database": "ERP",
  "trusted_connection": true,
  "driver": "ODBC Driver 18 for SQL Server",
  "encrypt": true,
  "trust_server_certificate": true
}
```
