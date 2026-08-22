"""
Agent layer for OrchestrAI.

Four agents, one job each:
  intake_agent   -> turns messy text into structured fields
  decision_agent -> turns structured fields into an action plan
  risk_agent     -> scores the plan 0-100 and explains why
  action_agent   -> actually performs the action (writes real state)

If GROQ_API_KEY is set in the environment, intake_agent will ask a Groq-hosted
model to do the extraction (better on messy, multi-language input). Otherwise
it falls back to a transparent keyword/regex rule engine so the whole system
still runs with zero external dependencies.
"""
import json
import os
import re
import time
import random

import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
FAILURE_SIMULATION_RATE = float(os.getenv("FAILURE_SIMULATION_RATE", "0.35"))

CATEGORY_KEYWORDS = {
    "Payment / Billing": ["payment", "refund", "charged", "billing", "invoice", "transaction"],
    "IT Incident": ["down", "failing", "error", "bug", "crash", "outage", "not working", "server"],
    "Customer Support": ["customer", "order", "delivery", "complain", "angry", "damaged"],
    "HR / Internal Ops": ["employee", "leave", "attendance", "payroll", "onboarding"],
    "Sales / Lead": ["lead", "demo request", "pricing", "quote", "prospect"],
}

DEPARTMENT_FOR_CATEGORY = {
    "Payment / Billing": "Finance + Technical",
    "IT Incident": "Technical Team",
    "Customer Support": "Customer Support",
    "HR / Internal Ops": "HR",
    "Sales / Lead": "Sales",
}

URGENCY_WORDS = [
    "immediately", "immediate", "urgent", "asap", "right now", "critical",
    "angry", "furious", "escalate", "several customers", "multiple customers",
    "not working", "outage",
]

# When two categories tie on keyword hits, prefer the more operationally
# severe one — an outage matters more than a generic support mention.
CATEGORY_SEVERITY_ORDER = [
    "IT Incident", "Payment / Billing", "Customer Support", "Sales / Lead", "HR / Internal Ops",
]


def _extract_amount(text):
    match = re.search(r"(?:₹|rs\.?|inr)\s?([\d,]+)", text, re.IGNORECASE)
    if match:
        return int(match.group(1).replace(",", ""))
    match = re.search(r"\$\s?([\d,]+)", text)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


def _rule_based_extract(text):
    lower = text.lower()

    category = "General Request"
    best_hits = 0
    for cat in CATEGORY_SEVERITY_ORDER:
        words = CATEGORY_KEYWORDS[cat]
        hits = sum(1 for w in words if w in lower)
        if hits > best_hits:
            best_hits = hits
            category = cat

    urgent_hits = [w for w in URGENCY_WORDS if w in lower]
    if len(urgent_hits) > 1 or "critical" in urgent_hits:
        priority = "Critical"
    elif urgent_hits or category in ("IT Incident", "Payment / Billing"):
        priority = "High"
    elif any(w in lower for w in ["please", "when you can", "no rush", "whenever convenient"]):
        priority = "Low"
    else:
        priority = "Medium"

    amount = _extract_amount(text)
    department = DEPARTMENT_FOR_CATEGORY.get(category, "General Ops")

    if "refund" in lower:
        intent = "Refund Request"
    elif category == "IT Incident":
        intent = "Incident Escalation"
    elif "complain" in lower or "angry" in lower or "damaged" in lower:
        intent = "Complaint Resolution"
    else:
        intent = "General Request"

    reasons = []
    if urgent_hits:
        reasons.append(f"urgency language detected ({', '.join(urgent_hits)})")
    if amount:
        reasons.append(f"financial amount identified (₹{amount:,})")
    if best_hits:
        reasons.append(f"matched {best_hits} keyword(s) for '{category}'")
    if not reasons:
        reasons.append("no strong urgency or financial signal found in the text")

    return {
        "intent": intent,
        "category": category,
        "department": department,
        "priority": priority,
        "amount": amount,
        "entities": {"amount": amount} if amount else {},
        "why_priority": "Priority set to " + priority + " because " + "; ".join(reasons) + ".",
        "source": "rule-engine",
    }


def _llm_extract(text):
    """Ask a Groq-hosted model to do the structured extraction. Falls back silently on any error."""
    if not GROQ_API_KEY:
        return None
    try:
        system = (
            "You are the Intake Agent inside OrchestrAI, an autonomous operations system. "
            "Read the user's messy operational request and return ONLY a compact JSON object "
            "with keys: intent, category, department, priority (Low/Medium/High/Critical), "
            "amount (number or null), why_priority (one sentence). No prose, no markdown fences."
        )
        resp = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "max_tokens": 300,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": text},
                ],
            },
            timeout=15,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        content = content.strip().strip("`")
        if content.startswith("json"):
            content = content[4:]
        data = json.loads(content)
        data["entities"] = {"amount": data.get("amount")} if data.get("amount") else {}
        data["source"] = "groq"
        return data
    except Exception:
        return None


class IntakeAgent:
    def analyze(self, text):
        llm_result = _llm_extract(text)
        if llm_result:
            return llm_result
        return _rule_based_extract(text)


class DecisionAgent:
    """Builds a concrete, ordered action plan from the intake understanding."""

    PLAYBOOKS = {
        "Refund Request": [
            "Verify customer and order",
            "Check original payment status",
            "Calculate refund amount",
            "Request human approval for refund",
            "Issue refund and notify customer",
        ],
        "Incident Escalation": [
            "Classify affected service",
            "Check current system status",
            "Create incident ticket",
            "Assign technical team",
            "Notify stakeholders",
        ],
        "Complaint Resolution": [
            "Log complaint against order/account",
            "Assess resolution options",
            "Route to senior support agent",
            "Notify customer of next steps",
        ],
        "General Request": [
            "Log request",
            "Route to relevant department",
            "Notify assigned owner",
        ],
    }

    REJECTION_PLAYBOOKS = {
        "Refund Request": [
            "No refund is issued",
            "Case flagged for manual follow-up",
            "Support manager notified of the rejection",
            "Customer notified that the refund was declined",
        ],
        "Incident Escalation": [
            "Incident is not auto-created",
            "Request flagged for manual triage",
            "On-call lead notified to review manually",
        ],
        "Complaint Resolution": [
            "Complaint left unresolved in the queue",
            "Escalated to a senior support agent for manual review",
        ],
        "General Request": [
            "Request left unactioned",
            "Flagged for manual review",
        ],
    }

    def build_plan(self, understanding):
        intent = understanding.get("intent", "General Request")
        steps = self.PLAYBOOKS.get(intent, self.PLAYBOOKS["General Request"])
        amount = understanding.get("amount")

        if intent == "Refund Request" and amount:
            action_type = "refund"
            primary_value = amount
            summary = f"Issue a refund of ₹{amount:,} to the customer."
        elif intent == "Incident Escalation":
            action_type = "create_incident"
            primary_value = understanding.get("category", "IT Incident")
            summary = f"Create an incident and assign it to {understanding.get('department')}."
        else:
            action_type = "create_task"
            primary_value = understanding.get("category", "General Request")
            summary = f"Create a task for {understanding.get('department')} and notify the owner."

        return {
            "steps": steps,
            "action_type": action_type,
            "primary_value": primary_value,
            "summary": summary,
        }

    def simulate(self, understanding, plan, scenario):
        """What-if: predict the downstream consequences of approve vs reject
        WITHOUT taking any action. Pure prediction, no side effects."""
        intent = understanding.get("intent", "General Request")
        if scenario == "reject":
            steps = self.REJECTION_PLAYBOOKS.get(intent, self.REJECTION_PLAYBOOKS["General Request"])
            headline = "If rejected:"
        else:
            steps = list(plan.get("steps", []))
            steps.append("Run Log entry written — action verified complete")
            headline = "If approved:"
        return {"scenario": scenario, "headline": headline, "predicted_steps": steps}


class RiskAgent:
    def score(self, understanding, plan):
        score = 10
        reasons = []

        priority = understanding.get("priority", "Medium")
        priority_points = {"Low": 0, "Medium": 10, "High": 25, "Critical": 40}
        score += priority_points.get(priority, 10)
        reasons.append(f"priority is {priority} (+{priority_points.get(priority, 10)})")

        amount = understanding.get("amount")
        if amount:
            if amount >= 20000:
                pts = 45
            elif amount >= 5000:
                pts = 30
            elif amount >= 1000:
                pts = 15
            else:
                pts = 5
            score += pts
            reasons.append(f"financial exposure of ₹{amount:,} (+{pts})")

        if plan.get("action_type") == "refund":
            score += 10
            reasons.append("action type is a refund, which is customer-financial (+10)")

        if understanding.get("category") == "IT Incident":
            score += 10
            reasons.append("customer-facing system incident (+10)")

        score = max(0, min(100, score))

        if score <= 30:
            band = "Safe"
        elif score <= 60:
            band = "Moderate"
        elif score <= 80:
            band = "High"
        else:
            band = "Critical"

        return {
            "score": score,
            "band": band,
            "why": "Risk scored " + str(score) + "/100 because " + "; ".join(reasons) + ".",
        }


class ActionAgent:
    """Performs the real, final action and returns a result the Run Log can display.

    Every call writes a real on-disk ticket file — that part never fails.
    The *external* leg (the simulated downstream API / notification call) can
    fail, in which case the Failure Recovery Agent retries, falls back to an
    alternative path, and escalates to a human if it still can't get through.
    """

    MAX_ATTEMPTS = 3

    def _write_ticket(self, record):
        ticket_dir = os.path.join(os.path.dirname(__file__), "data", "tickets")
        os.makedirs(ticket_dir, exist_ok=True)
        ticket_path = os.path.join(ticket_dir, f"{record['id']}.json")
        with open(ticket_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, default=str)
        return f"data/tickets/{record['id']}.json"

    def _attempt_external_call(self, record, attempt):
        """Simulates the downstream call (e.g. ticketing system / payment
        gateway). Attempt 1 and 2 use the primary channel; attempt 3 is
        framed as an alternative path, which is deliberately more reliable —
        that's the 'recovery' part of Failure Recovery."""
        failure_chance = FAILURE_SIMULATION_RATE if attempt < self.MAX_ATTEMPTS else FAILURE_SIMULATION_RATE * 0.3
        return random.random() > failure_chance

    def execute(self, record, external=True):
        """external=False is used for MANUAL-autonomy approvals: the AI is
        allowed to record the decision but NOT allowed to fire the external
        action itself — a human has to actually do it and confirm."""
        plan = record["plan"]
        action_type = plan.get("action_type")
        value = record.get("final_action_value", plan.get("primary_value"))
        request_id = record["id"]

        ticket_file = self._write_ticket(record)

        if not external:
            return {
                "success": True,
                "summary": f"Ticket #{request_id} filed. Awaiting manual execution by a human — the AI will not call any external system for a MANUAL-risk action.",
                "ticket_file": ticket_file,
                "attempts": [],
                "recovered": False,
                "escalated": False,
            }

        attempts = []
        success = False
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            ok = self._attempt_external_call(record, attempt)
            attempts.append({
                "attempt": attempt,
                "channel": "primary" if attempt < self.MAX_ATTEMPTS else "alternative",
                "success": ok,
            })
            if ok:
                success = True
                break

        escalated = not success

        if not success:
            summary = (
                f"Downstream call failed after {self.MAX_ATTEMPTS} attempts (primary + alternative path). "
                f"Ticket #{request_id} filed and escalated to a human for manual attention."
            )
        elif action_type == "refund":
            summary = f"Refund of ₹{value:,} processed and ticket #{request_id} filed."
        elif action_type == "create_incident":
            summary = f"Incident '{value}' created and assigned to the technical team (ticket #{request_id})."
        else:
            summary = f"Task created and routed (ticket #{request_id})."

        if success and len(attempts) > 1:
            summary += f" (recovered on attempt {attempts[-1]['attempt']} after {len(attempts) - 1} failed try/tries.)"

        return {
            "success": success,
            "summary": summary,
            "ticket_file": ticket_file,
            "attempts": attempts,
            "recovered": success and len(attempts) > 1,
            "escalated": escalated,
        }


def autonomy_mode_for_risk(score, auto_max, supervised_max):
    if score <= auto_max:
        return "AUTO"
    if score <= supervised_max:
        return "SUPERVISED"
    return "MANUAL"


intake_agent = IntakeAgent()
decision_agent = DecisionAgent()
risk_agent = RiskAgent()
action_agent = ActionAgent()
