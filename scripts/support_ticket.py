"""
Structured support ticket generation for escalations.

Run:
  python scripts/support_ticket.py
"""
import json
from enum import Enum
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()


class Priority(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
    URGENT = "urgent"


class Team(str, Enum):
    RETURNS   = "returns"
    BILLING   = "billing"
    TECHNICAL = "technical"
    ACCOUNT   = "account"
    GENERAL   = "general"


class SupportTicket(BaseModel):
    summary:            str = Field(description="One-line description of the issue")
    team:               Team = Field(description="Which team should handle this")
    priority:           Priority
    customer_sentiment: str = Field(description="frustrated/neutral/urgent/confused")
    what_was_tried:     str = Field(description="What the AI already attempted")
    suggested_action:   str = Field(description="First thing the human agent should do")
    context_summary:    str = Field(description="Key facts from the conversation")


TICKET_PROMPT = """You are a support escalation system for Acmera, an Indian e-commerce company.
A customer query could not be resolved by the AI assistant. Generate a structured support ticket.

Customer query: {query}
AI response attempted: {ai_response}
Reason for escalation: {reason}

Generate a SupportTicket with all fields filled accurately."""


def generate_ticket(query: str, ai_response: str, reason: str) -> SupportTicket:
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": TICKET_PROMPT.format(
                query=query,
                ai_response=ai_response,
                reason=reason,
            ),
        }],
        response_format=SupportTicket,
        temperature=0,
    )
    return response.choices[0].message.parsed


if __name__ == "__main__":
    escalations = [
        {
            "label": "Billing dispute",
            "query": "I was charged Rs. 12,999 twice for the same order ORD-887766. I need this resolved NOW or I will file a complaint with the consumer forum.",
            "ai_response": "I found information about payment policies but could not confirm the duplicate charge or initiate a refund.",
            "reason": "Billing dispute requiring transaction lookup and refund authorization beyond AI capability",
        },
        {
            "label": "Angry return demand",
            "query": "This is absolutely unacceptable! I returned my phone 2 weeks ago and still no refund. I have been calling daily. I want my Rs. 45,000 back TODAY or I will go to social media.",
            "ai_response": "Refunds are typically processed in 5-7 business days. I was unable to check the status of your specific return.",
            "reason": "High-value delayed refund with distressed customer requiring immediate escalation",
        },
        {
            "label": "Out of corpus query",
            "query": "I want to know Acmera's policy on bulk corporate purchases and GST invoice generation for orders above Rs. 5 lakh.",
            "ai_response": "I don't have enough context to answer this confidently. Please contact our support team.",
            "reason": "Low confidence — corporate bulk purchase policy not in knowledge base",
        },
    ]

    for i, case in enumerate(escalations, 1):
        print(f"\n{'='*70}")
        print(f"Escalation {i}: {case['label']}")
        print(f"Query: {case['query'][:80]}...")
        print(f"{'='*70}")
        ticket = generate_ticket(case["query"], case["ai_response"], case["reason"])
        print(json.dumps(ticket.model_dump(), indent=2))
