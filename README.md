# AI Social Media Manager

LangGraph-first social content pipeline. Built **feature by feature**.

## Feature 1 — Tavily web research (current)

1. User enters a topic
2. Backend runs LangGraph: `START → tavily_research → END`
3. Returns live web results via [Tavily](https://tavily.com)

### Setup

1. Get a free API key: https://app.tavily.com
2. Add to `.env`: `TAVILY_API_KEY=tvly-...`
3. Backend deps (once):

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd ..
```

4. Frontend deps (once, or `./run.sh` will install if missing):

```bash
cd frontend && npm install && cd ..
```

### Run backend + frontend together

```bash
chmod +x ./run.sh   # once
./run.sh
```

- Backend: http://localhost:8001 (API docs: `/docs`)
- Frontend: http://localhost:3000
- Ctrl+C stops both

API: `POST http://localhost:8001/api/research/tavily`

See [LANGGRAPH.md](LANGGRAPH.md) for the workflow and roadmap.
