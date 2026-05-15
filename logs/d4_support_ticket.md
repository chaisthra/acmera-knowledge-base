# S4.1 — Structured Escalation Tickets

## generate_ticket() Implementation

Uses `client.beta.chat.completions.parse()` with `response_format=SupportTicket` (Pydantic model).
Model: `gpt-4o-mini`, `temperature=0`. Guaranteed valid enum values for `team` and `priority` — no post-processing needed.

---

## Test Output — 3 Escalations

### Escalation 1: Billing Dispute
```json
{
  "summary": "Duplicate charge for order ORD-887766",
  "team": "billing",
  "priority": "urgent",
  "customer_sentiment": "frustrated",
  "what_was_tried": "I found information about payment policies but could not confirm the duplicate charge or initiate a refund.",
  "suggested_action": "Investigate the transaction for order ORD-887766 and process a refund for the duplicate charge.",
  "context_summary": "Customer was charged Rs. 12,999 twice for the same order and is threatening to file a complaint if not resolved immediately."
}
```

### Escalation 2: Angry Return Demand
```json
{
  "summary": "Delayed refund for returned phone",
  "team": "returns",
  "priority": "urgent",
  "customer_sentiment": "frustrated",
  "what_was_tried": "Informed the customer that refunds are typically processed in 5-7 business days and attempted to check the status of the return.",
  "suggested_action": "Investigate the status of the refund and expedite the process to ensure the customer receives their Rs. 45,000 refund immediately.",
  "context_summary": "Customer returned a phone 2 weeks ago and has not received a refund. They have been calling daily and are very distressed."
}
```

### Escalation 3: Out-of-Corpus Query
```json
{
  "summary": "Inquiry about bulk corporate purchases and GST invoice generation",
  "team": "billing",
  "priority": "high",
  "customer_sentiment": "confused",
  "what_was_tried": "Informed the customer to contact support team due to lack of information.",
  "suggested_action": "Provide detailed information on bulk corporate purchase policy and GST invoice generation.",
  "context_summary": "Customer is inquiring about Acmera's policy on bulk corporate purchases and GST invoices for orders above Rs. 5 lakh."
}
```

---

## Most Important Routing Field: `team`

`team` is the single most critical field because it is the only field that determines **which humans see the ticket**. Every other field (priority, sentiment, suggested_action) is metadata that a human agent reads after the ticket lands in their queue — but if it lands in the wrong queue, no one reads it at the right time.

**Production impact of consistent misrouting:**

| Misrouting scenario | Effect |
|---|---|
| Billing dispute → returns | Returns agent can't authorize a refund for a duplicate charge; re-routes to billing, customer waits an extra cycle |
| High-value return → billing | Billing has no RMS access; ticket bounces, SLA clock keeps ticking |
| Out-of-corpus → general | General team lacks authority to answer corporate GST policy; escalation stalls |

Cascading effects:
- **SLA breaches**: Each re-route adds 2-4 hours in typical CRM workflows. Urgent tickets breach their SLA before reaching the correct team.
- **Metric distortion**: Returns team shows inflated unresolved ticket count (tickets they can't close), billing team appears understaffed. Both metrics mislead capacity planning.
- **Customer rage amplification**: A frustrated customer who escalated once and gets bounced between teams is far more likely to go to social media or consumer forums — the exact outcome Escalation 1's customer threatened.
- **Agent frustration**: Agents who repeatedly receive tickets outside their scope complain to supervisors; this surfaces as a tooling/AI reliability problem and erodes trust in the system.

**Fix if misrouting is detected**: Add a human review step for the first 500 AI-generated tickets, compute routing accuracy per team, and fine-tune the prompt with misclassified examples. Alternatively, add a `routing_confidence` field and flag low-confidence tickets for manual triage before dispatch.
