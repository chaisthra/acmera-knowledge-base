# L5 — Load Testing: Baseline + Concurrency Ramp

## L5.1 Baseline (c=1, n=50)

| Metric | Value |
|---|---|
| Requests per second | 0.41 |
| p50 latency | 2,175 ms |
| p95 latency | 5,345 ms |
| Failed requests | 0 |

**p99 latency**: ~5,345 ms (p95 proxy — ab does not report p99 separately at n=50)

**Is p99 acceptable for a customer support system?**
Borderline. A 5.3s p95 means 1 in 20 users waits over 5 seconds for an answer. For an AI-powered support assistant, users tolerate slightly longer waits than a search box, but anything above 4–5s starts causing abandonment and follow-up contacts that defeat the purpose of automation. The high p95 here is caused by the guardrail stack (2 OpenAI calls before retrieval: `is_on_topic` + safety classifier) stacking on top of embedding + generation — so every request has 4 sequential OpenAI round-trips.

---

## L5.2 Concurrency Ramp

| Concurrency | Req/sec | p50 (ms) | p95 (ms) | Failed |
|---|---|---|---|---|
| c=1   | 0.41 | 2,175  | 5,345  | 0 |
| c=5   | 1.91 | 2,296  | 3,511  | 0 |
| c=20  | 5.71 | 2,419  | 4,740  | 0 |
| c=50  | 8.40 | 5,323  | 8,092  | 0 |
| c=100 | 8.37 | 11,025 | 13,664 | 0 |

---

## Inflection Point Analysis

**Inflection point: between c=20 and c=50.**

| Transition | p50 change | p95 change | Req/sec change |
|---|---|---|---|
| c=1 → c=5   | +121ms  (+6%)   | -1,834ms (p95 improves — parallelism) | +1.50 |
| c=5 → c=20  | +123ms  (+5%)   | +1,229ms (+35%)                        | +3.80 |
| c=20 → c=50 | +2,904ms (+120%) | +3,352ms (+71%)                       | +2.69 |
| c=50 → c=100 | +5,702ms (+107%) | +5,572ms (+69%)                      | -0.03 |

From c=1 to c=20, p50 stays flat (~2.2–2.4s) and throughput scales nearly linearly — the system handles concurrency well. At c=50, p50 more than doubles to 5.3s. At c=100, throughput plateaus at 8.37 req/sec (identical to c=50) while p50 doubles again to 11s. This throughput ceiling is the saturation signature — adding more concurrent users stops increasing work done and only increases wait time.

---

## Root Cause

**Primary bottleneck: OpenAI API concurrency + single Fargate task (0.5 vCPU)**

Each request makes 4 sequential external calls:
1. `is_on_topic()` → gpt-4o-mini (~500ms)
2. `check_input()` → gpt-3.5-turbo (~500ms)
3. `embed_query()` → text-embedding-3-small (~200ms)
4. `generate()` → gpt-4o-mini (~1,500ms)

At c=50, the single 0.5 vCPU Fargate task is handling 50 simultaneous requests each making 4 OpenAI calls = 200 concurrent outbound API calls. OpenAI's rate limits and the container's thread pool both start queuing at this point. The fact that req/sec flatlines at c=50→c=100 confirms the bottleneck is not the network or the ALB — it is the compute/API capacity of the single task.

**Auto-scaling mitigation**: The CPU target of 60% we configured should trigger scale-out before c=50 saturation in steady state. However, ECS takes ~90 seconds to spin up a new task, so burst spikes to c=50+ will still see the degradation window before the second task becomes healthy.

---

## Recommendations

| Fix | Impact | Effort |
|---|---|---|
| Cache common queries (already implemented) | Removes 3 of 4 OpenAI calls on cache hit | Done |
| Reduce guardrail to 1 call (merge topic + safety into one prompt) | Cuts ~500ms per request | Low |
| Increase Fargate task to 1 vCPU / 2GB | Handles more concurrent threads | Low (template change) |
| Lower auto-scaling CPU target from 60% → 40% | Scale-out triggers earlier | Low |
| Move to streaming responses | Reduces perceived latency at high concurrency | Medium |
