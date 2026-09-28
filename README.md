# 🚨 IncidentDeepDig

### AI Incident Response Agent with Persistent Hindsight Memory

> When production breaks, the answer is usually buried in a past incident, a Slack thread, or an old postmortem. **IncidentDeepDig turns that scattered history into living agent memory** using [Hindsight](https://hindsight.vectorize.io/) + [Groq](https://console.groq.com/) — so every new incident is met with evidence, not guesswork.

---

## 🎥 Demo

▶️ **Click to watch the walkthrough:**

[![Watch the IncidentDeepDig demo](images/Screenshot%202026-09-28%20195727.png)](images/Screen%20Recording%202026-09-28%20195553.mp4)

<sub>Videos: [Judge Mode demo](images/Screen%20Recording%202026-09-28%20195553.mp4) · [Feature tour](images/Screen%20Recording%202026-09-28%20195705.mp4)</sub>



---

## 💡 The idea in one loop

```
🚨 New incident
      ↓
🧠 Hindsight recalls similar past incidents
      ↓
🤖 Groq reasons over the evidence
      ↓
💡 Evidence-backed recommendation
      ↓
👨‍💻 Engineer confirms the outcome
      ↓
🧠 Hindsight retains it  →  better next time
```

The agent doesn't just answer. **It learns.**

---

## 🎬 Judge Mode — see memory change everything (60 sec)

The headline feature: run the **same incident twice** — once with memory off, once with Hindsight on — and watch generic guessing become an evidence-backed fix.

![Judge Mode — memory impact](images/Screenshot%202026-09-28%20195727.png)

| Without memory | With Hindsight |
| --- | --- |
| Generic troubleshooting | 3 relevant incidents recalled |
| No historical evidence | Previous root cause identified |
| Current incident only | Recalled evidence informs recommendations |

---

## ✨ Features

### 🕸️ Memory Graph
An interactive knowledge graph of everything the agent knows — incidents linked to the services they hit and the root-cause families they belong to. Hover any node to trace its relationships.

![Memory Graph](images/Screenshot%202026-09-28%20195748.png)

### 🔮 Pattern Insights
IncidentDeepDig mines memory for **recurring failure patterns** and **deployment risk** — so you can prevent the next outage, not just react to it. *(All numbers are computed from real data.)*

![Pattern Insights](images/Screenshot%202026-09-28%20195807.png)

### 📈 Agent Learning
Watch recall grow with every investigation, plus incident breakdowns by service.

![Agent Learning](images/Screenshot%202026-09-28%20195839.png)

### 🧠 Incident Memory & 📋 History
Everything retained in Hindsight, and every investigation with its reported outcome.

![Incident Memory](images/Screenshot%202026-09-28%20195826.png)
![Incident History](images/Screenshot%202026-09-28%20195852.png)

---

## 🏗️ Architecture

```
        ┌──────────────┐
        │   React UI   │  Judge Mode · Graph · Patterns · Learning
        └──────┬───────┘
               │  /api
        ┌──────▼───────┐
        │   FastAPI    │  investigate · feedback · graph · patterns
        └──────┬───────┘
        ┌──────┴───────┐
        ▼              ▼
  ┌──────────┐   ┌───────────┐
  │   Groq   │   │ Hindsight │  incidents · resolutions
  │ reasoning│   │  memory   │  feedback · learned patterns
  └──────────┘   └───────────┘
```

---

## 🚀 Quick start

**Prerequisites:** Python 3.10+, Node.js 18+, and API keys for [Hindsight](https://hindsight.vectorize.io/) and [Groq](https://console.groq.com/).

```bash
# 1. Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

# 2. Configure the required environment variables in a root .env file
# Create a root .env file using the variables in the Environment section below.

# 3. Seed memory with sample incidents (once)
python -m app.load_incidents

# 4. Run the API
python -m uvicorn app.api:app --port 8000
```

```bash
# 5. Frontend (second terminal)
cd frontend
npm ci
npm run dev        # opens http://localhost:5173
```

Keep both running — Vite proxies `/api` to the backend on port 8000.


---

## 🧭 The screens

| | Screen | What it shows |
| --- | --- | --- |
| 🎬 | **Judge Mode** | Memory ON vs OFF, the full learning loop in 60s |
| 🚨 | **Investigate** | Paste an incident → similar cases, recommendation, feedback |
| 🕸️ | **Memory Graph** | How incidents, services, and root causes connect |
| 🔮 | **Patterns** | Recurring failure patterns + deployment risk |
| 🧠 | **Memory** | Everything Hindsight remembers |
| 📈 | **Learning** | How recommendations improve as memory grows |
| 📋 | **History** | Every investigation and its outcome |

---

## 🛠️ Tech stack

**Hindsight** (long-term memory) · **Groq** (LLM reasoning) · **FastAPI** (Python API) · **React + Vite + TypeScript** (UI)

## Hindsight learning

Hindsight stores the seed postmortems and retrieves relevant memories for each investigation. Engineer feedback is retained with the incident context and remediation: **Worked** is recorded as `SUCCESS`, and **Didn't work** as `FAILURE` with a note that the remediation did not resolve the incident. Future investigations and the Patterns, Graph, and Learning/Metrics views use those accumulated memories. Seed loading is idempotent by incident ID.

## Environment

Set these required values in a root `.env` file:

```dotenv
HINDSIGHT_API_KEY=your_hindsight_api_key
GROQ_API_KEY=your_groq_api_key
```

Optional settings:

```dotenv
HINDSIGHT_API_URL=https://api.hindsight.vectorize.io
HINDSIGHT_BANK_ID=incidentiq
GROQ_MODEL=openai/gpt-oss-120b
```

`HINDSIGHT_BANK_ID` defaults to `incidentiq`; keep it consistent with the bank where your memories are stored. `HINDSIGHT_API_URL` and `GROQ_MODEL` have defaults shown above.

## Seed data and tests

Load the incidents from `data/incidents.json` into Hindsight:

```bash
python -m app.load_incidents
```

Install pytest in the active Python environment and run the backend suite from the project root:

```bash
python -m pip install pytest
python -m pytest
```

The scripts under `scripts/` are manual Hindsight API smoke checks, not automated tests. Run them only when the Hindsight environment variables are configured.

## Judge Mode

Judge Mode runs the same incident with memory disabled and enabled, then lets the engineer confirm whether the recommendation worked. The outcome is retained in Hindsight so future investigations can use that feedback.
