# LangGraph Workflow — AI Social Media Manager

## Feature 1 (current): Tavily web research

```text
User topic
  → POST /api/research/tavily
  → LangGraph: START → tavily_research → END
  → Live web results (title, url, snippet, score) + optional answer
  → JSON + frontend list
```

**Code**
- Graph: [`backend/app/graphs/tavily_graph.py`](backend/app/graphs/tavily_graph.py)
- Client: [`backend/app/services/tavily_client.py`](backend/app/services/tavily_client.py)
- API: [`backend/app/api/research.py`](backend/app/api/research.py)

### Setup

1. Get a free key at https://app.tavily.com
2. Add to `.env`:

```bash
TAVILY_API_KEY=tvly-...
```

3. Install deps and run:

```bash
./run.sh
```

### Test

```bash
curl -s -X POST http://localhost:8001/api/research/tavily \
  -H 'Content-Type: application/json' \
  -d '{"topic":"AI for founders automate tasks","limit":5}'
```

Or open the Next.js UI and click **Run web research**.

Gemini is **not** required for Feature 1.

---

## Why Tavily for production

- Official search API built for LLM/agent apps
- Structured results (title, url, content, score)
- Free tier for development; paid plans for live traffic
- Put the key only on the server; cache + rate-limit in production

---

## Roadmap

| # | Feature | Graph |
|---|---|---|
| 1 | Tavily web research | `START → tavily → END` (done) |
| 2 | Extra sources (news / papers) | parallel nodes |
| 3 | Merge + rate insights | join + rater |
| 4 | Planner | plan node |
| 5 | Writer | writer node |
| 6 | Human approval | interrupt |
| 7 | Publish | publish node |
