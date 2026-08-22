"""
Real background scheduler — this is what makes the 'it runs without you'
requirement true. A daemon thread wakes up every SCHEDULER_INTERVAL_SECONDS,
checks the on-disk schedule queue for due items, and runs each one through
the exact same process_workflow() used by manual submissions and webhooks.
It keeps running as long as the Flask process is alive, whether or not
anyone has the page open.
"""
import os
import threading
import time

from store import store
import core

INTERVAL = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "5"))
_started = False
_lock = threading.Lock()


def _tick_loop():
    while True:
        try:
            due = store.pop_due_scheduled_requests()
            for item in due:
                store.log_event(item["queue_id"], "Scheduled (cron) trigger fired — dispatching to the pipeline.")
                core.process_workflow(item["text"], "cron")
        except Exception as exc:
            # A scheduler tick should never crash the whole background thread.
            store.log_event("scheduler", f"Scheduler tick error: {exc}")
        time.sleep(INTERVAL)


def start():
    """Idempotent — safe to call more than once (e.g. under a dev reloader)."""
    global _started
    with _lock:
        if _started:
            return
        _started = True
        t = threading.Thread(target=_tick_loop, name="orchestrai-scheduler", daemon=True)
        t.start()
