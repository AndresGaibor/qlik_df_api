# Qlik Cloud API - Referencia para implementacion

## Endpoints documentados

### 1. Listar items (dataflows, scripts, datasets)

**URL:**
```
GET /api/v1/items?sort=-recentlyUsed&limit=24&spaceId={spaceId}&resourceType=app[dataflow-prep],app[single-table-prep],app[script],script[qvs],dataset[qix-df,qvd,connection_based_dataset]&noActions=true&next=
```

**Headers requeridos:**
- `accept: */*`
- Cookie de sesion Qlik

**Response:**
```json
{
  "data": [
    {
      "name": "Prueba de conexion S3",
      "spaceId": "6a57a14cf89e2c4d4b4d83af",
      "description": "Flujo para validar la conexion a S3",
      "resourceAttributes": {
        "_resourcetype": "app",
        "id": "7f4100b9-90d3-4ca3-b1d5-e249da1cf7de",
        "name": "Prueba de conexion S3",
        "usage": "DATAFLOW_PREP",
        "createdDate": "2026-07-15T16:18:03.732Z",
        "modifiedDate": "2026-07-15T16:18:04.069Z"
      },
      "resourceType": "app",
      "resourceSubType": "dataflow-prep",
      "resourceId": "7f4100b9-90d3-4ca3-b1d5-e249da1cf7de",
      "id": "6a57b2bca7882841882414d9",
      "links": {
        "open": {
          "href": "https://l676lvg3emfvcq2.us.qlikcloud.com/dataflow/7f4100b9-90d3-4ca3-b1d5-e249da1cf7de/overview"
        }
      }
    }
  ],
  "links": {
    "self": { "href": "..." }
  }
}
```

**Campos clave:**
- `resourceId` / `resourceAttributes.id`: ID del dataflow
- `name`: Nombre del dataflow
- `resourceSubType`: Tipo (`dataflow-prep`, `single-table-prep`)
- `spaceId`: ID del espacio
- `links.open.href`: URL para abrir el dataflow

---

### 2. Listar espacios

**URL:**
```
GET /api/v1/spaces?name=&limit=100&sort=%2Bname
```

**Headers requeridos:**
- `accept: */*`
- Cookie de sesion Qlik

**Response:**
```json
{
  "data": [
    {
      "id": "6a57a14cf89e2c4d4b4d83af",
      "type": "shared",
      "name": "mi-espacio",
      "description": "Espacio de ejemplo",
      "tenantId": "vGtoupIUZYcHq_6Q2MFn5r-eDCudinkh",
      "createdAt": "2026-07-15T15:03:40.138Z",
      "updatedAt": "2026-07-15T15:40:52.528Z"
    }
  ],
  "meta": { "count": 14 }
}
```

**Campos clave:**
- `id`: ID del espacio
- `name`: Nombre del espacio
- `type`: Tipo (`shared`, `managed`, `data`)

---

### 3. Listar automatizaciones

**URL:**
```
GET /api/v1/items?resourceType=automation&limit=50&noActions=true&sort=-updatedAt
```

**Headers requeridos:**
- `accept: */*`
- Cookie de sesion Qlik

**Response:**
```json
{
  "data": [
    {
      "name": "Test_BanCol",
      "spaceId": "6a57a14cf89e2c4d4b4d83af",
      "description": "Test_BanCol",
      "resourceAttributes": {
        "lastRunAt": "2026-07-17T16:15:30.000000Z",
        "lastRunStatus": "finished",
        "runMode": "manual",
        "state": "available"
      },
      "resourceType": "automation",
      "resourceId": "ee742da2-7b33-474a-8b2f-85c69ba0b8f0",
      "id": "6a57b338a788284188241776"
    }
  ]
}
```

**Campos clave:**
- `resourceId`: ID de la automatizacion
- `resourceAttributes.lastRunStatus`: Estado del ultimo run (`finished`, `failed`)
- `resourceAttributes.runMode`: Modo (`manual`, `scheduled`)

---

### 4. Detalle de automatizacion

**URL:**
```
GET /api/v1/automations/{automationId}
```

**Headers requeridos:**
- `accept: application/json`
- `qlik-csrf-token: {csrfToken}`
- `x-requested-with: XMLHttpRequest`
- Cookie de sesion Qlik

**Response:**
```json
{
  "id": "ee742da2-7b33-474a-8b2f-85c69ba0b8f0",
  "name": "Test_BanCol",
  "spaceId": "6a57a14cf89e2c4d4b4d83af",
  "state": "available",
  "description": "Test_BanCol",
  "workspace": {
    "blocks": [
      {
        "id": "15767545-8639-48C1-8254-5FA274C759B8",
        "name": "Start",
        "type": "StartBlock",
        "childId": "726AF387-4D60-46BE-92B5-D8E8E21D2681"
      }
    ]
  },
  "lastRun": {
    "id": "d2403538-e753-4aff-b0c8-20abe5885475",
    "status": "finished",
    "startTime": "2026-07-17T16:15:30.000000Z",
    "stopTime": "2026-07-17T16:15:30.000000Z"
  },
  "lastRunStatus": "finished",
  "runMode": "manual"
}
```

**Campos clave:**
- `workspace.blocks`: Lista de bloques del flujo
- `lastRun.status`: Estado del ultimo run
- `snippetIds`: IDs de snippets (scripts)
- `endpointIds`: IDs de endpoints (conectores)
- `connectorIds`: IDs de conectores usados

---

## Notas de implementacion

### Autenticacion
- Los endpoints de Qlik Cloud requieren cookie de sesion
- El `csrfToken` se obtiene de la cookie `_csrfToken`
- Las requests deben incluir headers de navegador para evitar bloqueos

### Paginacion
- El endpoint de items soporta paginacion via `next` en query params
- El campo `links.next` indica si hay mas resultados

### Resource Types para dataflows
- `app[dataflow-prep]`: Dataflows de Prepare
- `app[single-table-prep]`: Single table prep
- `app[script]`: Scripts Qlik
- `script[qvs]`: QlikView scripts
- `dataset[qix-df,qvd,connection_based_dataset]`: Datasets
