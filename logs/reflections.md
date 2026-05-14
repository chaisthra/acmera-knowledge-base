# Assignment Reflections

Collected across Weeks 1–4. Each entry is appended in order with timestamp and assignment stage.

---

## Week 2 / Session 3 — Chunking Strategy A/B Test (A1 Core)
**Date:** 2026-05-03 | **Stage:** Week 2, Session 1 | **Queries:** 50 | **Chunk size:** 500 | **Overlap:** 100

### Why Sliding Window Won

Sliding window achieved the highest overall correctness (4.64/5) and it comes down to one thing: boundary coverage. Policy documents are written in flowing prose — a condition on line 8 often depends on a definition from line 5. Fixed-size chunking cuts at a character limit regardless of sentence structure, so those cross-boundary details regularly end up split across two chunks with neither chunk containing the complete picture. Sliding window uses a 100-character overlap so every boundary region appears in two consecutive chunks, meaning the retriever almost always finds a chunk that contains the complete relevant policy detail.

Sentence-aware chunking avoids mid-sentence splits, which helped on payments (4.86) and products (4.75) where enumerated lists need to stay intact. But it cannot handle policies that span multiple paragraphs — warranty dropped to 4.00 because the conditions and exceptions for warranty coverage live across paragraph boundaries that sentence-aware treats as natural cut points.

The only category where fixed-size won was warranty (4.60), likely because warranty documents in this corpus happen to have short, self-contained paragraphs that fit cleanly within 500 characters without needing overlap to recover lost context.

All three strategies tied on retrieval hit rate (98%), which confirms chunking differences are a generation quality problem, not a retrieval problem — the right document is found regardless, but the chunk that reaches the LLM may or may not contain the specific detail needed.

---

## Week 2 / Session 3 — RAGAS Evaluation (A2.4)
**Date:** 2026-05-15 | **Stage:** Week 2, Session 3 | **Mode:** Dense retrieval

### Why Dense Over Hybrid

I chose dense retrieval for the RAGAS comparison because it consistently outperformed hybrid in our A2.3 eval. Despite adding synonym expansion and tuning the BM25 + RRF pipeline, the `account` and `warranty` categories never got the right document to rank #1. The vocabulary mismatch was too deep — the queries used terms like "safe" and "fix" while the corpus used "security" and "repair," and synonym expansion introduced noise that displaced the correct chunks rather than surfacing them. Dense retrieval, which operates in embedding space rather than keyword space, handled that mismatch better. So dense was the fair and honest choice for comparison.

### What the RAGAS Comparison Showed

**Faithfulness:** Our LLM-as-judge averaged 0.92 while RAGAS scored 0.63 — a gap of nearly 0.30. RAGAS flagged 6 out of 10 queries with a `△` (divergence > 0.15), all cases where it scored *lower* than our judge. This tells us our judge was being lenient. It was doing holistic assessment — if the answer *felt* grounded, it gave a high score. RAGAS decomposes the answer into individual claims and verifies each one against the retrieved context, which is a much stricter standard. Those 6 divergences are cases where specific claims in our answers were not strictly supported by the retrieved chunks, and our judge missed that.

**Correctness:** Both approaches landed close — our judge averaged 0.84, which is comparable. This makes sense because correctness is a semantic comparison against the expected answer, and both a human-style judge and RAGAS are doing roughly the same thing there.

**Context Precision:** Averaged 0.89, which is healthy. The two lower spots — q06 (returns, 0.59) and q27 (payments, 0.58) — indicate that for those queries, roughly half the retrieved chunks were not relevant to the question. That noise in retrieval likely contributed to lower faithfulness on those queries too.

### Key Takeaway

The faithfulness gap is the most important finding. Our judge said the system was 92% faithful; RAGAS said 63%. The truth is probably somewhere in between, but RAGAS is almost certainly closer — claim-level decomposition is a more rigorous standard than holistic impression. This means our pipeline is generating answers that *sound* well-grounded but contain specific details that the retrieved context doesn't actually support. That is a real risk in a customer support system where accuracy of policy details matters.

---

## Week 2 / Session 3 — Context Recall vs Hit Rate (A2 Challenge)
**Date:** 2026-05-15 | **Stage:** Week 2, Session 3 | **Mode:** Dense retrieval

### What Context Recall Catches That Hit Rate Doesn't

Hit rate is a binary, document-level check. It answers one question: did the right document appear anywhere in the top-K results? It says nothing about whether the specific chunk retrieved from that document actually contains the information needed to answer the question. A document can be 50 pages long — retrieving a chunk from page 3 when the answer is on page 47 still counts as a hit.

Context recall goes deeper. It checks whether the retrieved chunks contain the actual claims present in the ground truth answer. It is a measure of information coverage, not document coverage.

**The clearest example from our results is q15** (warranty, hard — "Will warranty apply if my laptop is stolen?"). Hit rate = yes, context recall = 0.00. We retrieved the warranty document, so hit rate was satisfied. But the specific chunk pulled did not contain any of the facts needed to answer the question — the policy detail about theft exclusions was in a different part of the document that our chunking did not surface. The pipeline confidently retrieved the right document, retrieved the wrong piece of it, and our hit rate metric never noticed.

**q06** (returns, medium) shows the reverse: hit rate = no, context recall = 0.50. We did not retrieve the primary returns document, but other chunks in the top-K contained enough overlapping information to cover half the ground truth claims. Hit rate penalised this; context recall gave partial credit, which is more honest about what the pipeline actually delivered.

Context recall is the better signal for whether retrieval is actually useful to generation. Hit rate is a fast sanity check; context recall tells you whether the right information made it through.

---

## Week 2 / Session 3 — LiteLLM Integration (A2 Stretch)
**Date:** 2026-05-15 | **Stage:** Week 2, Session 3 | **Mode:** Stretch goal

### What LiteLLM Gives You That the Raw SDK Doesn't

The fallback worked exactly as expected. When the primary model fails — whether due to a bad model name, a rate limit, or a quota exhaustion — LiteLLM silently retries with the next model in the fallback list. No query gets dropped, no exception surfaces to the user. That kind of resilience matters in a production customer support system where every failed query is a failed customer interaction.

More importantly, LiteLLM decouples our application code from any specific provider. If OpenAI changes their API, raises prices, or deprecates a model, we change one string — the model name — and nothing else in the codebase needs to touch. The same `litellm.completion()` call works identically across OpenAI, Anthropic, Azure, Gemini, and others. That is a meaningful engineering advantage: we built the pipeline once and can route it anywhere.

One clarification worth noting: the trace ID in the output comes from **LangFuse**, not LiteLLM. LangFuse's `@observe` decorator is generating and tracking that ID. LiteLLM has its own internal logging hooks, but in our pipeline, observability is owned by LangFuse. The two work independently and don't interfere with each other.

---
