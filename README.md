<<<<<<< HEAD
<<<<<<< HEAD
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

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure your keys in `.env` (do not commit this file):

   ```
   HINDSIGHT_API_URL=https://api.hindsight.vectorize.io
   HINDSIGHT_API_KEY=YOUR_HINDSIGHT_API_KEY
   GROQ_API_KEY=YOUR_GROQ_API_KEY
   HINDSIGHT_BANK_ID=incidentiq
   GROQ_MODEL=openai/gpt-oss-120b
   ```

## Usage (Phase 1)

Seed the memory bank with the synthetic incidents:

```bash
python -m app.load_incidents
```

Store a single first incident (alternative to the loader):

```bash
python app/test_hindsight.py
```

Recall it:

```bash
python app/test_recall.py
```

Run the full agent (recall + reason):

```bash
python -m app.main
```

## Web app (API + UI)

The Incident Command Center has a FastAPI backend and a React (Vite) frontend.

**1. Start the backend** (from `incidentiq/`, venv activated):

```bash
python -m uvicorn app.api:app --port 8000
```

Endpoints: `/api/health`, `/api/investigate`, `/api/feedback`,
`/api/memory`, `/api/history`, `/api/learning`.

**2. Start the frontend** (from `incidentiq/frontend/`):

```bash
npm install      # first time only
npm run dev      # serves http://localhost:5173
```

Vite proxies `/api` to the backend on port 8000, so run both together.

> Note: if `npm install` fails with `ENOTFOUND` against a corporate registry,
> the included `frontend/.npmrc` pins the public npm registry
> (`registry.npmjs.org`) to work around that.

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
=======
# Incident-response_agent
>>>>>>> e362b6a964ade42850bec55f5a49ef8f5c153b0e
=======

>>>>>>> origin/main
