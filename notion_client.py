"""
Real Notion integration — not a simulation.

If NOTION_TOKEN and the relevant database IDs are set in .env, this module
makes actual calls to the Notion API (api.notion.com) to create/update pages.
If they're not set, every function here is a silent no-op so the rest of the
system runs exactly the same without Notion configured.

Databases expected (create these in your Notion workspace, share each with
your integration, and paste the IDs into .env):

  NOTION_REQUESTS_DB_ID  — one page per request. Suggested properties:
    Name (title), Category (select), Department (select), Priority (select),
    Risk Score (number), Risk Band (select), Autonomy Mode (select),
    Status (select), Trigger (select), Human Decision (select),
    Final Value (number)

  NOTION_RUNLOG_DB_ID    — one page per audit-trail event. Suggested properties:
    Name (title) = the message, Request (rich_text) = request id,
    Timestamp (date)
"""
import os
import requests

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "").strip()
NOTION_REQUESTS_DB_ID = os.getenv("NOTION_REQUESTS_DB_ID", "").strip()
NOTION_RUNLOG_DB_ID = os.getenv("NOTION_RUNLOG_DB_ID", "").strip()
NOTION_VERSION = "2022-06-28"
NOTION_API = "https://api.notion.com/v1"

ENABLED = bool(NOTION_TOKEN and NOTION_REQUESTS_DB_ID)


def _headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _select(value):
    return {"select": {"name": str(value)[:100]}} if value else None


def create_request_page(record):
    """Creates a page in the Requests database. Returns the Notion page_id, or None."""
    if not ENABLED:
        return None
    try:
        u, r = record["understanding"], record["risk"]
        properties = {
            "Name": {"title": [{"text": {"content": u.get("intent", "Request")[:200]}}]},
            "Category": _select(u.get("category")),
            "Department": _select(u.get("department")),
            "Priority": _select(u.get("priority")),
            "Risk Score": {"number": r.get("score")},
            "Risk Band": _select(r.get("band")),
            "Autonomy Mode": _select(record.get("autonomy_mode")),
            "Status": _select(record.get("status")),
            "Trigger": _select(record.get("trigger_source")),
        }
        properties = {k: v for k, v in properties.items() if v is not None}
        resp = requests.post(
            f"{NOTION_API}/pages",
            headers=_headers(),
            json={"parent": {"database_id": NOTION_REQUESTS_DB_ID}, "properties": properties},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("id")
    except Exception:
        return None


def update_request_page(page_id, record):
    """Patches an existing Requests page after a human decision / execution."""
    if not ENABLED or not page_id:
        return False
    try:
        properties = {
            "Status": _select(record.get("status")),
            "Human Decision": _select(record.get("human_decision")),
        }
        if record.get("final_action_value") is not None:
            try:
                properties["Final Value"] = {"number": float(record["final_action_value"])}
            except (TypeError, ValueError):
                pass
        properties = {k: v for k, v in properties.items() if v is not None}
        resp = requests.patch(
            f"{NOTION_API}/pages/{page_id}",
            headers=_headers(),
            json={"properties": properties},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception:
        return False


def log_run_event(request_id, message):
    """Creates a row in the Run Log database. Silent no-op if not configured."""
    if not (NOTION_TOKEN and NOTION_RUNLOG_DB_ID):
        return None
    try:
        resp = requests.post(
            f"{NOTION_API}/pages",
            headers=_headers(),
            json={
                "parent": {"database_id": NOTION_RUNLOG_DB_ID},
                "properties": {
                    "Name": {"title": [{"text": {"content": message[:200]}}]},
                    "Request": {"rich_text": [{"text": {"content": request_id}}]},
                },
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("id")
    except Exception:
        return None
