# LangGraph Workflow — AI Social Media Manager

## Feature 2 (current): Multi-source research

```text
User topic
  → POST /api/research/multi
  → LangGraph (parallel):
        START → tavily_research  ─┐
        START → news_research    ─┼→ gather → END
        START → papers_research  ─┘
  → Web + News + Papers results
```

| Source | How | Key needed? |
|---|---|---|
| **Tavily** | Web search API | Yes — `TAVILY_API_KEY` |
| **News** | Google News RSS | No |
| **Papers** | Semantic Scholar API | No |

**Code**
- Graph: [`backend/app/graphs/research_graph.py`](backend/app/graphs/research_graph.py)
- Clients: `services/tavily_client.py`, `news_client.py`, `papers_client.py`
- API: [`backend/app/api/research.py`](backend/app/api/research.py)

### Setup

1. `TAVILY_API_KEY` in `.env` (https://app.tavily.com)
2. `./run.sh`

### Test

```bash
curl -s -X POST http://localhost:8001/api/research/multi \
  -H 'Content-Type: application/json' \
  -d '{"topic":"AI for founders automate tasks","limit":5}'
```

Feature 1 still works: `POST /api/research/tavily`

---

## Feature 1 (still available): Tavily only

`START → tavily_research → END` via `POST /api/research/tavily`

---

## Roadmap

| # | Feature | Status |
|---|---|---|
| 1 | Tavily web research | Done |
| 2 | News + papers (parallel) | Done |
| 3 | Merge + rate insights | Next |
| 4 | Planner | Planned |
| 5 | Writer | Planned |
| 6 | Human approval | Planned |
| 7 | Publish | Planned |
