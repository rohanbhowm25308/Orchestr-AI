#  OrchestrAI

### **AI handles the work. Humans stay in control.**

> **OrchestrAI is an autonomous AI operations agent that understands messy business requests, creates action plans, evaluates risk, decides how much autonomy is safe, and involves humans only when necessary.**

---

## 🌐 Live Demo

 **Try the Application**

https://orchestr-ai-retk.onrender.com

---

## 💻 GitHub Repository

 **Source Code**

https://github.com/rohanbhowm25308/Orchestr-AI/

---

---

##  What is OrchestrAI?

Modern organizations receive thousands of operational requests every day:

*  Refund requests
*  IT incidents
*  Customer complaints
*  HR requests
*  Sales and lead requests
*  General operational tasks

The problem isn't simply **understanding** these requests.

The real challenge is deciding:

> **"Should AI execute this automatically, ask a human for approval, or completely hand the action back to a human?"**

That's where **OrchestrAI** comes in.

It transforms an unstructured request into a complete operational workflow:

```text
User Request
     ↓
🧠 Intake Agent
     ↓
📋 Decision Agent
     ↓
⚠️ Risk Agent
     ↓
🤝 Autonomy Decision
     ↓
┌───────────────┬────────────────┬───────────────┐
│     AUTO      │   SUPERVISED   │    MANUAL     │
│ AI executes   │ Human approves │ Human acts    │
└───────────────┴────────────────┴───────────────┘
     ↓
 Action Agent
     ↓
 Failure Recovery
     ↓
 Audit / Run Log
```

---

#  Key Features

##  1. Multi-Agent AI Architecture

OrchestrAI separates responsibilities across specialized agents.

| Agent                 | Responsibility                   |
| --------------------- | -------------------------------- |
| 🧠 **Intake Agent**   | Understands messy user requests  |
| 📋 **Decision Agent** | Creates a structured action plan |
| ⚠️ **Risk Agent**     | Calculates operational risk      |
| ⚙️ **Action Agent**   | Executes approved actions        |
| 🔄 **Recovery Agent** | Handles failures and retries     |

This architecture makes the system easier to understand, extend, and control.

---

##  2. Intelligent Request Understanding

Users don't need to write perfectly structured commands.

For example:

```text
"Customer is angry because they were charged ₹8500 twice.
Please refund them immediately."
```

OrchestrAI can extract:

```text
Intent       → Refund Request
Category     → Payment / Billing
Department   → Finance + Technical
Priority     → Critical
Amount       → ₹8,500
```

The system supports:

### Rule-Based Intelligence

Works completely without an external AI API.

### Optional LLM Intelligence

When `GROQ_API_KEY` is configured, the Intake Agent can use a Groq-hosted LLM for more complex and messy requests.

---

#  3. Risk-Aware Autonomy

OrchestrAI doesn't blindly automate everything.

Every request receives a **0–100 risk score**.

### Risk Bands

|    Score | Risk        | Meaning                       |
| -------: | ----------- | ----------------------------- |
|   `0–30` | 🟢 Safe     | Low-risk operation            |
|  `31–60` | 🟡 Moderate | Requires controlled oversight |
|  `61–80` | 🟠 High     | Higher human involvement      |
| `81–100` | 🔴 Critical | Maximum human control         |

Risk is influenced by factors such as:

* Request priority
* Financial exposure
* Refund operations
* IT incidents
* Customer-facing impact

---

#  4. Three Levels of AI Autonomy

The heart of OrchestrAI is its **Human-in-the-Loop autonomy model**.

###  AUTO

Low-risk requests can be executed automatically.

```text
AI understands
      ↓
AI plans
      ↓
AI evaluates
      ↓
AI executes
```

No human approval required.

---

###  SUPERVISED

Medium-risk requests require human approval.

```text
AI understands
      ↓
AI plans
      ↓
AI evaluates
      ↓
👤 Human approves / modifies / rejects
      ↓
AI executes
```

---

###  MANUAL

High-risk operations never execute automatically.

```text
AI understands
      ↓
AI plans
      ↓
AI evaluates
      ↓
👤 Human performs the action
      ↓
👤 Human confirms completion
```

This prevents high-risk automation from becoming uncontrolled automation.

---

#  5. Role-Based AI Governance

OrchestrAI includes server-side permission enforcement.

###  Operator

* Can approve/reject Safe and Moderate requests
* Cannot modify AI-proposed values
* Cannot handle High/Critical decisions

###  Manager

* Can approve/reject/modify requests up to High risk
* Greater operational authority

###  Admin

* Full decision authority
* Can handle Critical requests
* Can modify autonomy thresholds

> Permissions are enforced on the **backend**, not just hidden in the frontend.

---

#  6. Failure Recovery System

What happens when an automated downstream action fails?

OrchestrAI doesn't immediately give up.

The Action Agent:

```text
Attempt 1
   ↓
❌ Failure
   ↓
Attempt 2
   ↓
❌ Failure
   ↓
🔄 Alternative Recovery Path
   ↓
Attempt 3
   ↓
✅ Recovered
```

If recovery still fails:

```text
 All attempts failed
       ↓
 Ticket preserved
       ↓
 Human escalation
```

The dashboard tracks recovery and escalation events.

---

#  7. Autonomous Scheduler

OrchestrAI can process scheduled requests without requiring the browser to remain open.

A background scheduler continuously checks the queue:

```text
Scheduled Request
       ↓
Schedule Queue
       ↓
Background Scheduler
       ↓
OrchestrAI Pipeline
       ↓
Risk Evaluation
       ↓
Action
```

This allows the system to behave like a real autonomous operations service.

---

#  8. Webhook Trigger

External systems can trigger OrchestrAI through an authenticated webhook.

```http
POST /api/webhook
```

Requests are protected using:

```text
X-Webhook-Secret
```

This makes it possible to connect OrchestrAI with external systems such as:

* Forms
* Support systems
* Internal tools
* Automation platforms
* Business workflows

---

#  9. What-If Simulation

Before taking an action, OrchestrAI can simulate possible outcomes.

For example:

```text
"What happens if this request is approved?"
```

or

```text
"What happens if this request is rejected?"
```

The Decision Agent predicts the resulting workflow without actually executing the action.

This provides an additional decision-support layer for humans.

---

#  10. Real Audit Trail

Every workflow generates timestamped events.

The Run Log can capture:

```text
Request received
↓
Intent detected
↓
Action plan generated
↓
Risk calculated
↓
Autonomy mode selected
↓
Human approval
↓
Action execution
↓
Recovery attempt
↓
Final result
```

This makes the system **observable and auditable** rather than acting like a black box.

---

#  11. Persistent Local Storage

OrchestrAI doesn't require a database server.

It maintains real on-disk state using JSON:

```text
data/
├── orchestrai.json
└── tickets/
    ├── request_1.json
    ├── request_2.json
    └── request_3.json
```

Each processed request can generate its own ticket record.

---

#  12. Optional Notion Integration

OrchestrAI can integrate with Notion when configured.

It can create/update:

* Request records
* Risk information
* Status
* Human decisions
* Final action values
* Run-log events

Notion integration is optional, so the core application can still run without it.

---

#  Architecture

```text
                         ┌─────────────────────┐
                         │   User / External   │
                         │       System        │
                         └──────────┬──────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
              Manual             Webhook           Scheduler
                 │                  │                  │
                 └──────────────────┼──────────────────┘
                                    ↓
                         ┌─────────────────────┐
                         │     Core Engine     │
                         └──────────┬──────────┘
                                    ↓
                         ┌─────────────────────┐
                         │    Intake Agent     │
                         │ Understand Request  │
                         └──────────┬──────────┘
                                    ↓
                         ┌─────────────────────┐
                         │   Decision Agent    │
                         │   Build Action Plan │
                         └──────────┬──────────┘
                                    ↓
                         ┌─────────────────────┐
                         │      Risk Agent     │
                         │    Score 0 → 100    │
                         └──────────┬──────────┘
                                    ↓
                         ┌─────────────────────┐
                         │ Autonomy Controller  │
                         └──────────┬──────────┘
                                    ↓
                    ┌───────────────┼───────────────┐
                    ↓               ↓               ↓
                  AUTO         SUPERVISED        MANUAL
                    │               │               │
                    │          Human Approval      │
                    │               │          Human Executes
                    └───────────────┼───────────────┘
                                    ↓
                         ┌─────────────────────┐
                         │    Action Agent     │
                         └──────────┬──────────┘
                                    ↓
                         ┌─────────────────────┐
                         │ Failure Recovery    │
                         └──────────┬──────────┘
                                    ↓
                         ┌─────────────────────┐
                         │   Audit / Run Log   │
                         └─────────────────────┘
```

---

#  Technology Stack

### Backend

* Python
* Flask
* Requests
* python-dotenv

### AI / Agentic Layer

* Multi-agent architecture
* Rule-based NLP
* Optional Groq LLM
* Risk scoring
* What-If simulation
* Autonomous decision routing

### Frontend

* HTML5
* CSS3
* JavaScript
* Interactive dashboard
* Live workflow monitoring

### Storage

* JSON-based persistence
* Local ticket records

### Integrations

* Groq API
* Notion API
* Authenticated Webhooks

### Deployment

* Gunicorn
* Flask production server support

---

#  Getting Started

## 1. Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/OrchestrAI.git
cd OrchestrAI
```

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment

Create a `.env` file from the example:

```bash
cp .env.example .env
```

On Windows, you can simply copy `.env.example` and rename it to:

```text
.env
```

The application can run without external API keys using the built-in rule engine.

For enhanced AI extraction, configure:

```env
GROQ_API_KEY=your_api_key
GROQ_MODEL=llama-3.3-70b-versatile
```

Optional configurations include:

```env
WEBHOOK_SECRET=your_webhook_secret
NOTION_TOKEN=your_notion_token
NOTION_REQUESTS_DB_ID=your_database_id
NOTION_RUNLOG_DB_ID=your_database_id
```

## 5. Run the Application

```bash
python app.py
```

Then open:

```text
http://localhost:5000
```

---

#  API Endpoints

| Method     | Endpoint               | Purpose                         |
| ---------- | ---------------------- | ------------------------------- |
| `POST`     | `/api/process`         | Process a request               |
| `POST`     | `/api/webhook`         | Authenticated external trigger  |
| `POST`     | `/api/schedule`        | Schedule a request              |
| `GET`      | `/api/schedule/queue`  | View scheduled requests         |
| `POST`     | `/api/approve`         | Approve / reject / modify       |
| `POST`     | `/api/complete-manual` | Confirm manual completion       |
| `POST`     | `/api/simulate`        | Run What-If simulation          |
| `GET/POST` | `/api/thresholds`      | Read/update autonomy thresholds |
| `GET`      | `/api/runlog`          | View audit events               |
| `GET`      | `/api/requests`        | View processed requests         |
| `GET`      | `/api/dashboard`       | Dashboard metrics               |
| `GET`      | `/api/status`          | System status                   |

---

#  Example Workflow

### Input

```text
"The customer was charged ₹8500 twice.
They are extremely angry and want the refund immediately."
```

### OrchestrAI

```text
🧠 Intake
   ↓
Intent: Refund Request
Category: Payment / Billing
Priority: Critical
Amount: ₹8,500

   ↓

📋 Decision
   ↓
Create refund action plan

   ↓

⚠️ Risk
   ↓
Risk Score: High/Critical

   ↓

🤝 Autonomy
   ↓
Human approval required

   ↓

👤 Manager/Admin
   ↓
Approve / Modify / Reject

   ↓

⚙️ Action
   ↓
Execute or route manually

   ↓

📜 Audit
   ↓
Complete workflow recorded
```

---

#  Why OrchestrAI Is Different

Traditional automation often follows:

```text
Trigger → Action
```

OrchestrAI follows:

```text
Trigger
   ↓
Understand
   ↓
Plan
   ↓
Evaluate Risk
   ↓
Determine Autonomy
   ↓
Human Governance
   ↓
Execute
   ↓
Recover
   ↓
Audit
```

The goal isn't to make AI **fully independent**.

The goal is to make AI **autonomous where it is safe and accountable where it matters**.

> ### **Autonomy without governance is automation risk.**
>
> ### **OrchestrAI is built around governed autonomy.**

---

#  Security Notes

Never commit your `.env` file or API keys to GitHub.

This project includes `.gitignore` rules for:

```text
.env
__pycache__/
*.pyc
data/orchestrai.json
data/tickets/*.json
```

Use `.env.example` to document required environment variables without exposing secrets.

---

#  Built For

**Microsoft AI Hackathon**

OrchestrAI was designed around a practical question:

> **How can organizations use autonomous AI without giving up human control?**

---

#  Author

### **Rohan Bhowmik**

AI/ML • Data Science • Generative AI • Agentic AI • Web Dev

---

#  License

This project is licensed under the **MIT License**.

---

###  If you find OrchestrAI interesting, consider giving the repository a star!

**OrchestrAI — Understand. Decide. Act. Recover. Audit.**
