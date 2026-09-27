# IncidentIQ

An AI production incident response assistant that learns from past incidents.

IncidentIQ combines **Hindsight** (long-term memory) with **Groq** (fast LLM
reasoning). When a new incident comes in, it recalls similar historical
incidents, reasons over them, and recommends investigation steps. After an
engineer resolves the incident, the outcome is retained back into memory so the
agent gets smarter over time.

```
incident
   -> recall() similar past incidents (Hindsight)
   -> reason over them (Groq)
   -> recommendation
   -> engineer resolves
   -> retain() outcome (Hindsight learns)
```

## Project structure

```
incidentiq/
├── .venv/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── memory.py            # Hindsight client (renamed to avoid shadowing the package)
│   ├── groq_client.py
│   ├── incident_agent.py
│   ├── load_incidents.py   # seed memory from data/incidents.json
│   ├── main.py
│   ├── test_hindsight.py
│   └── test_recall.py
├── data/
│   └── incidents.json
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

## Install and run

### Prerequisites

- Python 3.10 or later
- Node.js 18 or later and npm
- API keys for [Hindsight](https://hindsight.vectorize.io/) and [Groq](https://console.groq.com/)

### 1. Clone the repository

```bash
git clone <repository-url>
cd incidentiq
```

### 2. Create a Python environment and install dependencies

```bash
python -m venv .venv
```

Activate it, then install the Python packages:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```bash
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure API keys

Copy `.env.example` to `.env` and add your Hindsight and Groq API keys:

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# macOS/Linux
cp .env.example .env
```

Keep `.env` private; do not commit it.

### 4. (Optional) Seed incident memory

This loads the sample incidents from `data/incidents.json` into Hindsight. Run it once if you want the app to start with historical context:

```bash
python -m app.load_incidents
```

### 5. Start the backend

From the repository root, with the Python environment activated:

```bash
python -m uvicorn app.api:app --reload --port 8000
```

Leave this terminal running. The API is available at `http://localhost:8000`.


### 6. Start the frontend

Open a second terminal, go to the repository's `frontend` directory, then install and start the UI:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. Keep both terminals running; Vite forwards `/api` requests to the backend on port 8000.

The API endpoints are `/api/health`, `/api/investigate`, `/api/feedback`, `/api/memory`, `/api/history`, and `/api/learning`.

Vite proxies `/api` to the backend on port 8000, so run both together.

> If `npm install` fails with `ENOTFOUND` against a corporate registry, the included `frontend/.npmrc` pins the public npm registry (`registry.npmjs.org`).

### The four screens

- **🚨 Investigate** — paste an incident; see similar past incidents (with
  similarity %), the AI recommendation, investigation steps, and
  This Worked / Didn't Work feedback (successful outcomes are retained back
  into Hindsight).
- **🧠 Memory** — everything remembered in Hindsight.
- **📈 Learning** — how the agent improves as memory grows.
- **📋 History** — every investigation and its reported outcome.

## Roadmap

- **Phase 1** — Python project, Groq + Hindsight connected, first response ✅
- **Phase 2** — Incident data model, synthetic incidents, better memory structure
- **Phase 3** — Agent workflow, resolution feedback, learning loop
- **Phase 4** — FastAPI REST APIs ✅
- **Phase 5** — Frontend incident dashboard ✅
- **Phase 6** — Demo mode (before memory / after memory)
- **Phase 7** — Docker, GitHub, deployment
- **Phase 8** — 60-second demo video + README polish
