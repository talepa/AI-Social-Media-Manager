# AI Social Media Manager

LangGraph research desk: gather sources, then build a downloadable report on demand.

## Flow

1. **Research** — `POST /api/research/multi` (web + news + papers)  
2. **Generate report** — `POST /api/research/synthesize` (compile by default; optional Gemini)  
3. **Download** — Markdown · JSON · PDF/Print (HTML)  

Identical topics (normalized) are **cached on disk** for 24h by default — set `force_refresh: true` or use **Refresh sources** in the UI to bypass.

### Setup

```bash
# .env
TAVILY_API_KEY=...
GOOGLE_API_KEY=...   # only for “Enhance with AI”

cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd ..
./run.sh
```

- App: http://localhost:3000  
- Docs: http://localhost:8001/docs  

See [LANGGRAPH.md](LANGGRAPH.md).
