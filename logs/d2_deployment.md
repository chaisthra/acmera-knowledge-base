# D2 Deployment Deliverable

## Stack: acmera-kb-dev (ap-south-1)

### Stack Outputs (CloudFormation → acmera-kb-dev → Outputs)

| Key | Value |
|-----|-------|
| APIEndpoint | |
| DBEndpoint | |
| ECRRepository | |

---

### Live API Test

```
curl -X POST <APIEndpoint>/query \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is the return window?"}'
```

**Response:**
```json

```

---

### Ingest Log (19 documents)

```

```

---

### ECS Service Status (ECS → Clusters → acmera-dev → Services)

- Cluster: acmera-dev
- Service status:
- Running tasks:
- Task definition:

---

### RDS Instance (RDS → Databases → acmera-dev)

- Engine: PostgreSQL 16.6
- Instance class: db.t3.micro
- Status:
- Endpoint:
