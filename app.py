"""
OrchestrAI — AI Autonomous Operations Agent
Flask backend.

Run:
    pip install -r requirements.txt
    cp .env.example .env      # fill in keys if you have them (optional)
    python app.py

Then open http://localhost:5000
"""
import os
import time
import uuid

from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv

# This MUST run before importing core/agents/scheduler/roles — agents.py
# reads GROQ_API_KEY (and other settings) from the environment at MODULE
# IMPORT time, not inside a function. If load_dotenv() ran after those
# imports, agents.py would have already cached an empty string, and no
# amount of a correct .env file would ever fix it. Explicit path too, since
# plain load_dotenv() only searches the current working directory and
# silently finds nothing if the server is launched from anywhere else.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

import core
import scheduler
import roles as roles_module
from store import store

app = Flask(__name__, static_folder="static", template_folder="templates")

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()

scheduler.start()


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# --------------------------------------------------------------------------
# Core workflow
# --------------------------------------------------------------------------

@app.route("/api/process", methods=["POST"])
def process_request():
    payload = request.get_json(force=True) or {}
    text = (payload.get("text") or "").strip()
    trigger_source = payload.get("trigger_source", "manual")
    if not text:
        return jsonify({"error": "Request text is required."}), 400
    record = core.process_workflow(text, trigger_source)
    if isinstance(record, dict) and record.get("error"):
        return jsonify(record), 400
    return jsonify(record), 200


@app.route("/api/webhook", methods=["POST"])
def webhook():
    """Real authenticated webhook trigger — a genuine external system (e.g.
    a form backend or a support tool) can POST here. Closed by default:
    without WEBHOOK_SECRET set in .env, the endpoint refuses everything."""
    if not WEBHOOK_SECRET:
        return jsonify({"error": "Webhook trigger is disabled. Set WEBHOOK_SECRET in .env to enable it."}), 503
    provided = request.headers.get("X-Webhook-Secret", "")
    if provided != WEBHOOK_SECRET:
        return jsonify({"error": "Invalid or missing X-Webhook-Secret header."}), 401
    payload = request.get_json(force=True) or {}
    text = (payload.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Request text is required."}), 400
    record = core.process_workflow(text, "webhook")
    return jsonify(record), 200


@app.route("/api/schedule", methods=["POST"])
def schedule_request():
    """Real cron-style trigger: queues a request to be picked up by the
    background scheduler thread, independent of the browser or this request."""
    payload = request.get_json(force=True) or {}
    text = (payload.get("text") or "").strip()
    delay_seconds = int(payload.get("delay_seconds", 20))
    if not text:
        return jsonify({"error": "Request text is required."}), 400
    item_id = str(uuid.uuid4())[:8]
    run_at = time.time() + max(3, delay_seconds)
    store.queue_scheduled_request(text, run_at, item_id)
    store.log_event(item_id, f"Scheduled to run in {delay_seconds}s via cron trigger.")
    return jsonify({"queue_id": item_id, "run_at_epoch": run_at, "delay_seconds": delay_seconds}), 200


@app.route("/api/schedule/queue")
def schedule_queue():
    return jsonify(store.get_schedule_queue())


@app.route("/api/approve", methods=["POST"])
def approve_request():
    payload = request.get_json(force=True) or {}
    request_id = payload.get("request_id")
    decision = payload.get("decision")
    modified_value = payload.get("modified_value")
    role = payload.get("role", "operator")
    record, status = core.approve_workflow(request_id, decision, modified_value, role)
    return jsonify(record), status


@app.route("/api/complete-manual", methods=["POST"])
def complete_manual():
    payload = request.get_json(force=True) or {}
    request_id = payload.get("request_id")
    record, status = core.complete_manual_execution(request_id)
    return jsonify(record), status


@app.route("/api/simulate", methods=["POST"])
def simulate():
    payload = request.get_json(force=True) or {}
    request_id = payload.get("request_id")
    scenario = payload.get("scenario", "approve")
    result, status = core.simulate_workflow(request_id, scenario)
    return jsonify(result), status


@app.route("/api/thresholds", methods=["GET", "POST"])
def thresholds():
    if request.method == "GET":
        auto_max, supervised_max = core.get_thresholds()
        return jsonify({"auto_max": auto_max, "supervised_max": supervised_max})

    payload = request.get_json(force=True) or {}
    role = payload.get("role", "operator")
    if not roles_module.can_change_thresholds(role):
        return jsonify({"error": "Only Admin accounts can change autonomy thresholds."}), 403
    auto_max = int(payload.get("auto_max", 30))
    supervised_max = int(payload.get("supervised_max", 75))
    core.set_thresholds(auto_max, supervised_max)
    store.log_event("policy", f"Admin updated autonomy thresholds: AUTO<={auto_max}, SUPERVISED<={supervised_max}.")
    return jsonify({"auto_max": auto_max, "supervised_max": supervised_max})


# --------------------------------------------------------------------------
# Visibility: run log + dashboard
# --------------------------------------------------------------------------

@app.route("/api/runlog")
def run_log():
    return jsonify(store.get_events(limit=200))


@app.route("/api/requests")
def all_requests():
    return jsonify(store.get_all_requests())


@app.route("/api/dashboard")
def dashboard():
    return jsonify(store.compute_metrics())


@app.route("/api/status")
def status():
    import agents
    return jsonify({
        "groq_enabled": bool(agents.GROQ_API_KEY),
        "webhook_enabled": bool(WEBHOOK_SECRET),
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    # use_reloader is off even in debug mode: this app writes to data/*.json
    # on every request, and the reloader's file-watcher would restart the
    # server on its own writes.
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
