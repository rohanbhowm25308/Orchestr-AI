"""
Lightweight JSON-file store. No database server required, so the whole
project runs anywhere with just `python app.py`. Everything written here
is real, on-disk state — this is the audit trail the run log surfaces.

Exposes a module-level singleton `store` so every module (app, core,
scheduler) shares the same on-disk state without passing an instance around.
"""
import json
import os
import threading
import time
from datetime import datetime


class Store:
    _DEFAULT_DATA = {"requests": {}, "events": [], "schedule_queue": []}

    def __init__(self, db_path):
        self.db_path = db_path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        # Covers both "file doesn't exist yet" and "file exists but is empty/
        # corrupted" (e.g. a 0-byte file left over from an interrupted write,
        # or one created empty by an editor/git checkout) — either way, we
        # want a valid JSON file on disk before anything tries to read it.
        needs_init = True
        if os.path.exists(db_path):
            try:
                with open(db_path, "r", encoding="utf-8") as f:
                    json.load(f)
                needs_init = False
            except (json.JSONDecodeError, ValueError):
                needs_init = True
        if needs_init:
            self._write(dict(self._DEFAULT_DATA))

    def _read(self):
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, ValueError, FileNotFoundError):
            # Self-heal: an empty/corrupt file shouldn't take the whole app
            # down on every single request. Reset to a valid empty state.
            data = dict(self._DEFAULT_DATA)
            self._write(data)
        data.setdefault("schedule_queue", [])
        data.setdefault("requests", {})
        data.setdefault("events", [])
        return data

    def _write(self, data):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    # ---------------------------------------------------------------- events

    def log_event(self, request_id, message, actor="system"):
        with self._lock:
            data = self._read()
            data["events"].append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "epoch": time.time(),
                "request_id": request_id,
                "message": message,
                "actor": actor,
            })
            self._write(data)

    def get_events(self, limit=200):
        data = self._read()
        return list(reversed(data["events"]))[:limit]

    # -------------------------------------------------------------- requests

    def save_request(self, record):
        with self._lock:
            data = self._read()
            data["requests"][record["id"]] = record
            self._write(data)

    def get_request(self, request_id):
        data = self._read()
        return data["requests"].get(request_id)

    def get_all_requests(self):
        data = self._read()
        items = list(data["requests"].values())
        items.sort(key=lambda r: r.get("created_at_epoch", 0), reverse=True)
        return items

    def find_recent_duplicate(self, text, trigger_source, window_seconds=60):
        data = self._read()
        now = time.time()
        for record in data["requests"].values():
            if record.get("raw_text") == text and record.get("trigger_source") == trigger_source:
                created = record.get("created_at_epoch", 0)
                if now - created <= window_seconds:
                    return record
        return None

    # --------------------------------------------------------- schedule queue

    def queue_scheduled_request(self, text, run_at_epoch, item_id):
        with self._lock:
            data = self._read()
            data["schedule_queue"].append({
                "queue_id": item_id,
                "text": text,
                "run_at_epoch": run_at_epoch,
                "status": "queued",
            })
            self._write(data)

    def pop_due_scheduled_requests(self):
        """Atomically pull every queued item whose run_at_epoch has passed."""
        with self._lock:
            data = self._read()
            now = time.time()
            due = [i for i in data["schedule_queue"] if i["status"] == "queued" and i["run_at_epoch"] <= now]
            for item in due:
                item["status"] = "dispatched"
            self._write(data)
            return due

    def get_schedule_queue(self):
        data = self._read()
        return sorted(data["schedule_queue"], key=lambda i: i["run_at_epoch"])

    # --------------------------------------------------------------- metrics

    def compute_metrics(self):
        data = self._read()
        items = list(data["requests"].values())
        total = len(items)
        auto = sum(1 for r in items if r["autonomy_mode"] == "AUTO")
        supervised = sum(1 for r in items if r["autonomy_mode"] == "SUPERVISED")
        manual = sum(1 for r in items if r["autonomy_mode"] == "MANUAL")
        approved = sum(1 for r in items if r.get("human_decision") == "approve")
        modified = sum(1 for r in items if r.get("human_decision") == "modify")
        rejected = sum(1 for r in items if r.get("human_decision") == "reject")
        completed = sum(1 for r in items if r["status"] in ("completed", "manually_completed"))
        pending = sum(1 for r in items if r["status"] == "pending_approval")
        awaiting_manual = sum(1 for r in items if r["status"] == "ready_for_manual_execution")
        avg_risk = round(sum(r["risk"]["score"] for r in items) / total, 1) if total else 0

        human_decisions = approved + modified + rejected
        override_rate = round((modified / human_decisions) * 100, 1) if human_decisions else 0
        approval_rate = round(((approved + modified) / human_decisions) * 100, 1) if human_decisions else 0

        decision_times = []
        for r in items:
            if r.get("decided_at_epoch") and r.get("created_at_epoch"):
                decision_times.append(r["decided_at_epoch"] - r["created_at_epoch"])
        avg_decision_seconds = round(sum(decision_times) / len(decision_times), 1) if decision_times else 0

        duplicates_prevented = sum(1 for e in data["events"] if "Duplicate event detected" in e["message"])

        failed_actions = 0
        recovered_actions = 0
        escalated_actions = 0
        for r in items:
            result = r.get("result") or {}
            attempts = result.get("attempts") or []
            if len(attempts) > 1:
                if result.get("recovered"):
                    recovered_actions += 1
                if result.get("escalated"):
                    escalated_actions += 1
                    failed_actions += 1

        return {
            "total_requests": total,
            "auto_executed": auto,
            "supervised": supervised,
            "manual": manual,
            "completed": completed,
            "pending_approval": pending,
            "awaiting_manual_execution": awaiting_manual,
            "human_approved": approved,
            "human_modified": modified,
            "human_rejected": rejected,
            "approval_rate": approval_rate,
            "override_rate": override_rate,
            "avg_risk_score": avg_risk,
            "avg_decision_seconds": avg_decision_seconds,
            "duplicates_prevented": duplicates_prevented,
            "failed_actions": failed_actions,
            "recovered_actions": recovered_actions,
            "escalated_actions": escalated_actions,
        }


_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "orchestrai.json")
store = Store(db_path=_db_path)
