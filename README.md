# Acmera Knowledge Base — RAG System for E-commerce Customer Support

A production RAG system that answers customer queries over a 19-document policy corpus covering returns, payments, membership, warranty, shipping, and more.

Built and iterated layer by layer from naive retrieval to a deployed, evaluated, and hardened pipeline.


---

## What it does

Takes a customer query, runs it through a full retrieval and generation pipeline, and returns a grounded answer with full observability via LangFuse.

---

## Architecture

```
User Query
  → PII Anonymization (Presidio)
  → Input Guardrail (topic restriction + prompt injection check)
  → Semantic Cache (Redis, 0.92 cosine threshold)
      ↓ cache miss
  → Embed Query (text-embedding-3-small)
  → Filtered Dense Retrieval (scoped to intent-relevant docs, top_k x 2)
  → Cohere Cross-Encoder Rerank (rerank-v4.0-pro)
  → Context Expansion (neighbouring chunks, window=1)
  → Deduplication (Jaccard similarity, threshold=0.75)
  → Compression (max 2000 tokens, highest scored first)
  → Order by Source
  → Assemble Context
  → Difficulty Classifier (GPT-4o-mini, score 1-5)
      → GPT-4o for score > 3
      → GPT-4o-mini for score ≤ 3
  → Generation (LiteLLM with fallback)
  → Output Guardrail (hallucination detection + PII restore)
  → Response
```

---

## Eval Results

Evaluated against a 64-query golden dataset spanning 14 categories and easy, medium, and adversarial difficulty levels. Half human written, half synthetically generated.

| Metric | Score |
|---|---|
| Retrieval Hit Rate | 98% |
| MRR | 0.93 |
| Avg Faithfulness | 4.80 / 5 |
| Avg Correctness | 4.72 / 5 |

RAGAS integration included for cross-framework comparison.
Regression testing and baseline validation in place.
All eval runs traced in LangFuse.

---

## Load Test Results

Apache Bench, 50 concurrent users, 2000 requests.

| Metric | Value |
|---|---|
| p50 | 2.8s |
| p95 | 7.2s |
| p99 | 36.2s |

Inflection point at c=50. Single 0.5 vCPU Fargate task saturates at 89% CPU.
Scale-out to 2 tasks takes 61 seconds. Requests during that window hit the saturated task.

Semantic cache reduces p95 from 34s to 3.7s at c=20 on repeated queries.

---

## Known Gaps and Planned Fixes

| Gap | Fix |
|---|---|
| No real-time alerting on rate limit hits or silent failures | AWS SNS alerts on error rate and unanswered queries |
| No automated document ingestion pipeline | Trigger-based ingestion on document change |
| No index refresh when corpus is updated | Automated re-embed and upsert pipeline |
| ECS task takes 61s to warm up on scale-out | Set MinCapacity to 2, lower CPU threshold to 40% |
| Two guardrail LLM calls add latency | Merge into single prompt |

---

## AWS Deployment

- ECS Fargate (0.5 vCPU, 1GB RAM)
- ALB with health check on /health
- RDS PostgreSQL with pgvector extension
- Redis for semantic cache
- Auto-scaling: 1 to 3 tasks above 60% CPU
- CloudWatch monitoring
- LangFuse for full trace observability

---

## Setup

### Prerequisites

- Python 3.11+
- Docker Desktop
- OpenAI API key
- Cohere API key
- LangFuse account (cloud.langfuse.com free tier)

### Local

```bash
cp .env.example .env
# Fill in API keys
docker-compose up -d
pip install -r requirements.txt
python scripts/setup_db.py
python scripts/ingest.py
python scripts/demo.py
```

### Deploy to AWS

```bash
docker build --platform linux/amd64 -t project-a .
docker push $AWS_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/acmera-kb-dev:latest
sam deploy --stack-name acmera-kb-dev --region ap-south-1 --capabilities CAPABILITY_IAM --guided
```

---

## Repo Structure

```
project-a/
├── corpus/                  # 19 Acmera policy documents
├── scripts/
│   ├── setup_db.py          # pgvector table + HNSW index
│   ├── ingest.py            # chunk + embed + store
│   ├── rag.py               # core RAG pipeline
│   ├── semantic_cache.py    # Redis-backed semantic cache
│   ├── input_guardrail.py   # topic + safety classifier
│   ├── output_guardrail.py  # hallucination detection
│   ├── pii_anonymizer.py    # Presidio anonymize + restore
│   ├── difficulty_classifier.py  # query routing 1-5
│   ├── eval_harness.py      # hit rate, MRR, faithfulness, correctness
│   └── demo.py              # interactive CLI
├── api.py                   # FastAPI wrapper
├── Dockerfile
├── template.yaml            # AWS SAM template
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Corpus

19 markdown documents covering: returns, payments, membership tiers, warranty, shipping, promotions, electronics catalog, sustainability, corporate gifting, and support FAQs.
```

