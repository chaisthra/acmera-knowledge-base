# L5 — Bottleneck Analysis (c=50 observed data)

## Setup
- Load: `ab -n 500 -c 50` against `/query`
- Monitored simultaneously: ECS Metrics, CloudWatch Logs tail, Langfuse traces

---

## Q1: Where did most latency go?

**Observed:** Langfuse span breakdown showed `query_embedding` at **700ms** — normally ~200ms under no load, inflated 3.5x under c=50 concurrency. CloudWatch logs showed request timestamp bunching just before c=50 hit, confirming requests were queuing in the Fargate thread pool before even starting processing.

**Conclusion:** Two compounding factors:
1. **Queuing** — the single 0.5 vCPU task cannot dispatch 50 concurrent threads fast enough; requests stack up waiting for a free slot
2. **OpenAI API latency inflation** — with 50 concurrent requests each making 4 OpenAI calls, the embedding API slows from ~200ms to 700ms under shared rate-limit pressure

Most wall-clock time at c=50 was queue wait, not actual processing. The pipeline spans themselves were inflated but the dominant cost was time sitting before the pipeline started.

---

## Q2: What % did ECS CPU reach at peak?

**Observed: 89.29%**

The auto-scaling threshold is set at **60% CPU**. The task blew through it to 89.29%, meaning auto-scaling did trigger — but ECS takes ~90 seconds to start a new Fargate task and pass health checks. During that 90-second window, all 500 requests absorbed the full saturation. By the time a second task came online, the ab run was already past peak load.

**Takeaway:** The threshold is right but the response time is too slow for burst traffic. Auto-scaling helps steady-state load, not spikes.

---

## Q3: Did any requests fail? What HTTP error code and why?

**Observed: 0 failed requests.**

No 502/504 errors despite CPU hitting 89.29%. This is because:
- The ALB idle timeout is 60s and ab's `-s 120` flag kept connections alive long enough
- The Fargate task queued requests rather than dropping them — uvicorn's default worker pool held requests in memory and processed them slowly rather than rejecting them
- The guardrail stack (4 OpenAI calls per request) adds latency but doesn't fail under load — OpenAI rate-limits by slowing responses, not returning errors at this concurrency level

The cost of zero failures was very high p95 (8,092ms) — the system chose latency over errors.

---

## Q4: If you had to handle 10x this load tomorrow, what single change would you make first?

**Increase Fargate task CPU from 0.5 vCPU to 2 vCPU.**

Reasoning from the observed data:
- CPU hit 89.29% at c=50. 10x load = c=500 equivalent pressure
- More vCPU means more concurrent threads dispatched simultaneously, reducing queue depth directly
- This is a one-line change in `template.yaml` (`Cpu: 512` → `Cpu: 2048`) and is immediately deployable
- It also makes auto-scaling more effective — each task handles more load before saturating, so fewer cold-start windows

The second change would be **merging the two guardrail LLM calls** (`is_on_topic` + `check_input`) into a single prompt, cutting 4 OpenAI calls per request to 3. But the CPU bottleneck needs to be fixed first — adding API calls to an already-saturated task makes it worse.

---

## Summary Table

| Concurrency | Req/sec | p50 (ms) | p95 (ms) | Failed | CPU Peak |
|---|---|---|---|---|---|
| c=1   | 0.41 | 2,175  | 5,345  | 0 | — |
| c=5   | 1.91 | 2,296  | 3,511  | 0 | — |
| c=20  | 5.71 | 2,419  | 4,740  | 0 | — |
| c=50  | 8.40 | 5,323  | 8,092  | 0 | **89.29%** |
| c=100 | 8.37 | 11,025 | 13,664 | 0 | — |

**Inflection point: c=20 → c=50** — p50 jumps 120%, throughput plateaus, CPU saturates.
