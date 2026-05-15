# D2 ECS Observation Questions

## Q1. How many tasks are running? What CPU and memory is allocated to each?

- Running tasks: 1
- CPU: 0.5 vCPU
- Memory: 1 GiB
- Platform version: 1.4.0

---

## Q2. Uvicorn startup log line (ECS → Task → Logs tab)

Uvicorn is listening on port **8080**.

---

## Q3. How long does ECS take to start a replacement after stopping the task?

**2 minutes 30 seconds** from clicking Stop until the new task reached RUNNING status.

---

## Q4. Why does ECS replace it automatically? What setting controls this?

ECS Services → Configuration tab shows **Desired tasks = 1**. The ECS service scheduler continuously reconciles actual vs desired task count — when a task stops, it automatically launches a replacement to maintain the desired count.

---

## Q5. Where in the task definition is the Docker image URI stored?

ECS → Task Definitions → acmera-dev → Container definitions → Image field:

```
706059253942.dkr.ecr.ap-south-1.amazonaws.com/acmera-kb-dev:latest
```

---

## Q6. Which environment variables come from Secrets Manager vs plain env vars?

**Plain environment variables:**
- `PG_HOST`, `PG_PORT`, `PG_USER`, `PG_DATABASE`
-  `LANGFUSE_HOST`, 

**From Secrets Manager** (fixed in template — uses `ValueFrom` referencing `DBSecret`):
- `PG_PASSWORD` ,`COHERE_API_KEY`,`OPENAI_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`,— injected from `acmera/dev/db` secret, key `password`


