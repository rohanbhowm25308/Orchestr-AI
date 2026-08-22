# OrchestrAI

**AI handles the work. Humans stay in control.**

An autonomous AI operations agent built for the Microsoft AI Hackathon. It takes a
messy, real-world request, understands it, drafts an action plan, scores the risk of
carrying it out, and only pauses for a human when the action is genuinely risky. Every
run leaves a real, timestamped, role-gated audit trail — and if a downstream action
fails, a Recovery Agent retries before escalating to a human.

```
Trigger → Intake → Decision → Risk → Human (if needed) → Action → Run Log
```

## Stack

- **Backend:** Python, Flask, `python-dotenv`, `requests`
- **Frontend:** plain HTML, CSS, JavaScript — no build step, no framework
- **AI:** rule-based extraction by default; if you set `GROQ_API_KEY` in `.env`, the
  Intake Agent calls a Groq-hosted model instead, for better results on messy or
  multi-language text
- **Storage:** a single JSON file (`data/orchestrai.json`) plus one real ticket file per
  request under `data/tickets/` — genuine on-disk state, not a simulated log

**Groq is the only external API key anywhere in this project.** Everything else —
roles, the run log, the scheduler, the webhook trigger, failure recovery — is
self-contained and needs no third-party account.

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env      # optional — the app works fully with this left blank
python app.py
```

Open **http://localhost:5000**.

## What each piece does

| Layer | File | Job |
|---|---|---|
| Intake Agent | `agents.py` → `IntakeAgent` | Turns free text into intent / category / department / priority |
| Decision Agent | `agents.py` → `DecisionAgent` | Builds an action plan; also predicts What-If outcomes |
| Risk Agent | `agents.py` → `RiskAgent` | Scores the plan 0–100 and explains why |
| Action Agent | `agents.py` → `ActionAgent` | Executes: writes a ticket file, retries on simulated failure |
| Roles | `roles.py` | Operator / Manager / Admin permission checks, enforced server-side |
| Scheduler | `scheduler.py` | Background thread — real cron trigger, runs independent of the browser |
| Core | `core.py` | Shared workflow logic used by manual, webhook, and cron triggers alike |
| Store | `store.py` | JSON-file persistence: requests, run log, schedule queue, metrics |
| API | `app.py` | Routes — see below |
| UI | `templates/index.html`, `static/` | Submit panel, pipeline, live agent monitor, collaboration graph, approvals, run log, dashboard |

## API routes

| Route | Purpose |
|---|---|
| `POST /api/process` | Manual / form trigger |
| `POST /api/webhook` | Authenticated webhook trigger — requires header `X-Webhook-Secret` matching `WEBHOOK_SECRET`; closed (503) if that env var is unset |
| `POST /api/schedule` | Queue a request to run automatically after N seconds, picked up by the background scheduler |
| `GET  /api/schedule/queue` | See queued/dispatched scheduled items |
| `POST /api/approve` | Approve / reject / modify a pending request (role-checked) |
| `POST /api/complete-manual` | Confirm a MANUAL-risk action was carried out by a human |
| `POST /api/simulate` | What-If: predict the approve or reject outcome without taking any action |
| `GET/POST /api/thresholds` | Read or (Admin-only) change the AUTO/SUPERVISED/MANUAL risk thresholds live |
| `GET /api/runlog`, `/api/requests`, `/api/dashboard`, `/api/status` | Visibility |

## Autonomy modes

Risk score decides how much say a human gets, configurable in `.env` or live via the
Admin threshold panel:

- **0–30 → AUTO** — executes immediately, no approval needed
- **31–75 → SUPERVISED** — AI proposes, a human approves / modifies / rejects, then the
  AI executes automatically on approval
- **76–100 → MANUAL** — AI drafts and files the ticket but will **not** call any external
  system itself. A human has to carry the action out and click "Mark as completed
  manually" to close it — the AI only recommends here, it never executes.

A modified value (e.g. a human changing a ₹8,500 refund to ₹5,000) is recorded as an
override and shown in the dashboard's override rate.

## Permission-aware roles

Pick a role from the nav bar — this isn't cosmetic, the server enforces it on every
decision:

- **Operator** — approve/reject Safe or Moderate risk only; cannot modify AI-proposed values
- **Manager** — approve/reject/modify up to High risk
- **Admin** — everything, including Critical risk and changing the autonomy thresholds

## Failure Recovery Agent

Every executed action calls a simulated downstream system (the real ticket file always
writes successfully — only that *external* leg is simulated). `FAILURE_SIMULATION_RATE`
in `.env` controls how often that call fails on its first two attempts. On failure, the
Action Agent retries, falls back to an "alternative path" with a better success chance,
and if that still fails, escalates to a human — all visible in the Run Log and counted
on the dashboard (Actions recovered / Escalated after failure).

## What-If Simulation

While a request is paused for approval, click "What if I approve?" or "What if I
reject?" to see the Decision Agent's predicted downstream steps — a pure prediction,
no side effects.

## Real multi-trigger infrastructure

- **Manual** — the demo panel's Run button, via `/api/process`
- **Webhook** — `/api/webhook`, a real authenticated endpoint any external system can
  call (set `WEBHOOK_SECRET` to enable it — it's a password you invent yourself, not a
  third-party credential)
- **Cron** — `/api/schedule` queues an item; a genuine background thread
  (`scheduler.py`) picks it up and runs it on schedule, whether or not the browser tab
  is open

## Try it

The demo panel has four one-click examples that exercise all three autonomy modes:
a damaged-order refund (supervised), a payment outage (supervised/critical), a routine
leave request (auto), and a large urgent refund (manual). Switch the role picker in the
nav to see permission enforcement.

## Notes on the "AI" in Adaptive Autonomy

The rule-based intake engine is intentionally transparent — every priority and risk
score comes with a one-sentence "why," visible in the UI, rather than a black-box
number. Swapping in the Groq-backed extractor (`GROQ_API_KEY`) keeps that same
`why_priority` field, so the explanation stays visible either way.

## Deploying

`gunicorn` is already in `requirements.txt`. Use a single worker
(`gunicorn app:app --workers 1`) since the scheduler thread and the JSON-file store
aren't designed to be shared safely across multiple processes.
