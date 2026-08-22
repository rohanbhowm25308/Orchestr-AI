"""
Shared workflow core: Trigger -> Intake -> Decision -> Risk -> (Human) ->
Action -> Log. The manual API route, the authenticated webhook route, and
the background scheduler all call into this module so every trigger type
runs through the exact same logic — nothing trigger-specific lives in app.py.
"""
import os
import time
import uuid
from datetime import datetime

from agents import intake_agent, decision_agent, risk_agent, action_agent, autonomy_mode_for_risk
from store import store
import roles as roles_module

_thresholds = {
    "auto_max": int(os.getenv("RISK_AUTO_MAX", 30)),
    "supervised_max": int(os.getenv("RISK_SUPERVISED_MAX", 75)),
}


def get_thresholds():
    return _thresholds["auto_max"], _thresholds["supervised_max"]


def set_thresholds(auto_max, supervised_max):
    _thresholds["auto_max"] = auto_max
    _thresholds["supervised_max"] = supervised_max


def _now_str():
    return datetime.now().strftime("%H:%M:%S")


def _log_attempts(request_id, result):
    for a in result.get("attempts", []):
        outcome = "succeeded" if a["success"] else "failed"
        store.log_event(request_id, f"Action attempt {a['attempt']} via {a['channel']} channel — {outcome}.")
    if result.get("recovered"):
        store.log_event(request_id, "Failure Recovery Agent: action recovered after retrying.")
    if result.get("escalated"):
        store.log_event(request_id, "Failure Recovery Agent: all attempts failed — escalated to a human.")


def process_workflow(text, trigger_source):
    text = (text or "").strip()
    if not text:
        return {"error": "Request text is required."}

    dup = store.find_recent_duplicate(text, trigger_source, window_seconds=60)
    if dup:
        store.log_event(dup["id"], "Duplicate event detected — execution prevented.")
        return {"duplicate": True, "original": dup}

    request_id = str(uuid.uuid4())[:8]
    now_epoch = time.time()

    store.log_event(request_id, f"Request received via {trigger_source} trigger.")

    understanding = intake_agent.analyze(text)
    store.log_event(request_id, f"Intent classified as '{understanding['intent']}'.")

    plan = decision_agent.build_plan(understanding)
    store.log_event(request_id, "Action plan drafted.")

    risk = risk_agent.score(understanding, plan)
    auto_max, supervised_max = get_thresholds()
    mode = autonomy_mode_for_risk(risk["score"], auto_max, supervised_max)
    store.log_event(request_id, f"Risk scored at {risk['score']}/100 ({risk['band']}). Mode: {mode}.")

    record = {
        "id": request_id,
        "created_at": _now_str(),
        "created_at_epoch": now_epoch,
        "decided_at_epoch": None,
        "trigger_source": trigger_source,
        "raw_text": text,
        "understanding": understanding,
        "plan": plan,
        "risk": risk,
        "autonomy_mode": mode,
        "status": "pending_approval" if mode != "AUTO" else "auto_approved",
        "human_decision": None,
        "decided_by_role": None,
        "final_action_value": plan.get("primary_value"),
        "result": None,
    }

    store.save_request(record)

    if mode == "AUTO":
        store.log_event(request_id, "Risk within auto-execute threshold. No human approval required.")
        result = action_agent.execute(record, external=True)
        _log_attempts(request_id, result)
        record["result"] = result
        record["status"] = "completed" if result["success"] else "escalated"
        record["decided_at_epoch"] = time.time()
        store.save_request(record)
    else:
        store.log_event(request_id, "Paused for human approval.")

    return record


def approve_workflow(request_id, decision, modified_value, role):
    record = store.get_request(request_id)
    if not record:
        return {"error": "Request not found."}, 404
    if record["status"] != "pending_approval":
        return {"error": "Request is not awaiting approval."}, 400

    allowed, reason = roles_module.can_decide(role, record["risk"]["band"], decision)
    if not allowed:
        return {"error": reason}, 403

    role_norm = roles_module.normalize_role(role)
    record["human_decision"] = decision
    record["decided_by_role"] = role_norm
    record["decided_at_epoch"] = time.time()

    if decision == "reject":
        store.log_event(request_id, f"Human ({role_norm}) rejected the proposed action.")
        record["status"] = "rejected"
        record["result"] = {
            "summary": "No action taken. Case flagged for manual follow-up.",
            "success": True,
            "attempts": [],
        }
        store.save_request(record)
        return record, 200

    if decision == "modify":
        record["final_action_value"] = modified_value
        store.log_event(
            request_id,
            f"Human ({role_norm}) modified action: AI proposed {record['plan'].get('primary_value')} "
            f"-> human set {modified_value}.",
        )
    else:
        store.log_event(request_id, f"Human ({role_norm}) approved the AI's recommendation as-is.")

    if record["autonomy_mode"] == "MANUAL":
        result = action_agent.execute(record, external=False)
        record["result"] = result
        record["status"] = "ready_for_manual_execution"
        store.log_event(
            request_id,
            "MANUAL-risk action: AI will not auto-execute. Awaiting human confirmation of manual completion.",
        )
    else:
        result = action_agent.execute(record, external=True)
        _log_attempts(request_id, result)
        record["result"] = result
        record["status"] = "completed" if result["success"] else "escalated"
        store.log_event(request_id, f"Action executed: {result['summary']}")

    store.save_request(record)
    return record, 200


def complete_manual_execution(request_id):
    record = store.get_request(request_id)
    if not record:
        return {"error": "Request not found."}, 404
    if record["status"] != "ready_for_manual_execution":
        return {"error": "Request is not awaiting manual execution."}, 400
    record["status"] = "manually_completed"
    store.log_event(request_id, "Human confirmed the action was completed manually outside the system.")
    store.save_request(record)
    return record, 200


def simulate_workflow(request_id, scenario):
    record = store.get_request(request_id)
    if not record:
        return {"error": "Request not found."}, 404
    prediction = decision_agent.simulate(record["understanding"], record["plan"], scenario)
    return prediction, 200
