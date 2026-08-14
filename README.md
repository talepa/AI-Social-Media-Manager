# AI Social Media Manager

LangGraph-first social content pipeline. Built **feature by feature**.

## Feature 2 — Multi-source research (current)

Parallel LangGraph nodes:

1. **Tavily** — web search  
2. **News** — Google News RSS (free)  
3. **Papers** — Semantic Scholar (free)  

### Setup

1. Get a Tavily key: https://app.tavily.com  
2. Add to `.env`: `TAVILY_API_KEY=tvly-...`  
3. Backend deps (once):

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd ..
```

### Run

```bash
./run.sh
```

- Frontend: http://localhost:3000  
- Multi research: `POST http://localhost:8001/api/research/multi`  
- Tavily only: `POST http://localhost:8001/api/research/tavily`  
- Docs: http://localhost:8001/docs  

See [LANGGRAPH.md](LANGGRAPH.md) for the workflow and roadmap.
