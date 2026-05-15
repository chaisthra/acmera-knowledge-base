"""
Acmera Knowledge Base Assistant — FastAPI
D1.1 endpoints:  GET /health  |  POST /query  |  POST /ingest
Web UI endpoints: GET /       |  POST /api/ask  |  GET /assets/*

Run locally:
  uvicorn api:app --host 0.0.0.0 --port 8080 --reload
Then open http://localhost:8080
"""
import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

ROOT_DIR      = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR   = os.path.join(ROOT_DIR, "scripts")
WEB_DIR       = os.path.join(ROOT_DIR, "web")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

app = FastAPI(title="Acmera Knowledge Base API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory=SCRIPTS_DIR), name="assets")


# ─────────────────────────────────────────
# D1.1 Core Endpoints
# ─────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


class QueryRequest(BaseModel):
    query: str
    mode: str = "advanced"


@app.post("/query")
def query(req: QueryRequest):
    from rag import ask
    result = ask(req.query, mode=req.mode)
    return {"answer": result["answer"], "trace_id": result.get("trace_id")}


@app.post("/ingest")
def ingest():
    from ingest import ingest as run_ingest
    run_ingest()
    return {"status": "done"}


# ─────────────────────────────────────────
# Web UI Endpoints
# ─────────────────────────────────────────

class AskRequest(BaseModel):
    query: str
    mode: str = "dense"
    use_cache: bool = True


@app.post("/api/ask")
def ask_endpoint(req: AskRequest):
    from rag import ask
    from output_guardrail import check_output, check_hallucination

    # ask() handles input guardrail + PII anonymization internally
    try:
        result = ask(req.query, mode=req.mode, use_cache=req.use_cache)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if result.get("blocked"):
        return {
            "query":           req.query,
            "answer":          result["answer"],
            "blocked":         True,
            "block_category":  result.get("block_category"),
            "chunks":          [],
            "trace_id":        None,
            "trace_url":       None,
            "elapsed_seconds": 0,
            "cache_hit":       False,
            "cache_similarity": None,
            "mode":            req.mode,
            "confidence":      None,
            "ticket":          None,
        }

    # ── Output PII scan ──────────────────────────────────────────────────
    pii_check = check_output(result["answer"])
    answer = pii_check["redacted"] if not pii_check["safe"] else result["answer"]

    # ── Hallucination check ──────────────────────────────────────────────
    hallucination = {"has_hallucination": False, "unsupported_claims": []}
    if result.get("context"):
        try:
            hallucination = check_hallucination(answer, result["context"])
        except Exception:
            pass

    chunks = []
    for c in result.get("retrieved_chunks", []):
        if "cohere_score" in c:
            score, score_type = c["cohere_score"], "cohere"
        elif "rrf_score" in c:
            score, score_type = c["rrf_score"], "rrf"
        else:
            score, score_type = c.get("similarity", 0), "cosine"
        chunks.append({
            "doc_name":    c["doc_name"],
            "chunk_index": c["chunk_index"],
            "score":       round(float(score), 4),
            "score_type":  score_type,
            "content":     c["content"],
        })

    trace_id  = result.get("trace_id")
    trace_url = f"{LANGFUSE_HOST}/trace/{trace_id}" if trace_id else None

    return {
        "query":                req.query,
        "answer":               answer,
        "chunks":               chunks,
        "trace_id":             trace_id,
        "trace_url":            trace_url,
        "elapsed_seconds":      result.get("elapsed_seconds"),
        "cache_hit":            result.get("cache_hit", False),
        "cache_similarity":     result.get("cache_similarity"),
        "mode":                 req.mode,
        "confidence":           result.get("confidence"),
        "blocked":              False,
        "has_hallucination":    hallucination["has_hallucination"],
        "unsupported_claims":   [c["claim"] for c in hallucination.get("unsupported_claims", [])],
        "pii_redacted":         not pii_check["safe"],
        "ticket":               result.get("ticket"),
    }


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))
