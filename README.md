# Atelier — Research Intelligence Platform

Atelier is a **multi-agent research intelligence platform** built with FastAPI, LangGraph, and Gemini. It decomposes technical questions into structured investigation plans, dispatches specialist agents to gather evidence from multiple sources, and synthesizes cited research reports.

The repo folder is named *AI Social Media Manager*; the running application is **Atelier**.

| | URL |
|---|---|
| App | `http://localhost:3000` |
| API | `http://localhost:8001` |
| OpenAPI | `http://localhost:8001/docs` |

---

## Quick Start

```bash
cp .env.example .env          # add API keys (see Environment below)
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd ..
cd frontend && npm install && cd ..
./run.sh
```

Open **http://localhost:3000** to use the research desk UI.

---

## Architecture

Atelier runs a **Director → Specialists → Evidence → Synthesis** pipeline orchestrated by LangGraph with checkpointed state.

```
                    USER
                     │
                     ▼
              Research Question
                     │
                     ▼
           ┌─────────────────────┐
           │  Research Director   │  Gemini structured output
           │  (agents/director)   │  Decomposes question → InvestigationPlan
           └────────┬────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌──────────┐
   │   Web   │ │Academic │ │Repository│   Specialist agents
   │Specialist│ │Specialist│ │Specialist│   (wired — Phase 2)
   └────┬────┘ └────┬────┘ └────┬─────┘
        │           │           │
        └───────────┼───────────┘
                    ▼
           ┌─────────────────┐
           │ Evidence Analyst │   (wired — Phase 5)
           └────────┬────────┘
                    ▼
           ┌─────────────────┐
           │   Synthesizer   │   (wired — Phase 6)
           └────────┬────────┘
                    ▼
              Cited Report
```

### What's Built

**Research Director** (`backend/app/agents/director.py`)
- Gemini decomposes a question into bounded sub-questions and picks specialists
- Budgets are deterministic from depth (quick: 3 tasks/6 tools, standard: 5/12, deep: 8/20) — never LLM-decided
- Falls back to rule-based plan when the LLM is unavailable or returns bad output
- 11 unit tests covering budgets, fallback paths, truncation, and markdown fence stripping

**Checkpointed Session Graph** (`backend/app/graphs/session_graph.py`)
- Full session lifecycle: gather → repeated chat turns on one thread
- LangGraph `interrupt()` for human-in-the-loop: pauses for expand-research or mode-switch proposals
- `Command(resume=...)` to accept/decline — server-side conversation state, no client-side history needed
- Checkpointer via `app.services.checkpointer` (Postgres when `DATABASE_URL` works, else `MemorySaver`)

**Investigation Graph** (`backend/app/graphs/investigation_graph.py`)
- `START → initialize_run → director → specialists → evidence_analyst → synthesis → END`
- Same checkpointer factory as the session graph; state shaped as a superset for later phases
- Event log tracks `run_started`, `plan_created`, `specialists_completed`, `evidence_analysis_completed`, `synthesis_completed`, `citation_validated`
- Tool budget from depth is split across sub-questions; specialists run in parallel
- Evidence Analyst consolidates findings into `CLAIM-*` records with strength/conflicts/gaps
- Synthesizer emits a cited markdown report; citation validator rejects invented IDs
- `POST /runs/stream` emits SSE as each phase advances; completed runs via `GET /runs/{id}` (Postgres or in-memory store)

**Parallel Source Gather** (`backend/app/graphs/research_graph.py`)
- LangGraph parallel fan-out to web, news, papers, and GitHub nodes
- Conditional routing: only selected source nodes run (not all four self-skipping)
- Results normalized, merged, and cached

---

## LangGraph Graphs

Atelier has three LangGraph graphs:

| Graph | File | Purpose |
|---|---|---|
| **Research** | `graphs/research_graph.py` | Parallel source fetch (Tavily, News, Papers, GitHub) |
| **Session** | `graphs/session_graph.py` | Checkpointed multi-turn chat with `interrupt()` |
| **Investigation** | `graphs/investigation_graph.py` | Director → (Specialists → Evidence → Synthesis, building out) |

Session + investigation graphs share `get_checkpointer()`: **PostgresSaver** when `DATABASE_URL` is reachable, otherwise **MemorySaver**. Investigation run metadata (SSE / `GET /runs/{id}`) uses the same rule via `INVESTIGATION_STORE`. With Postgres, state survives restarts; with memory, use a single uvicorn worker.

---

## API Endpoints

### Research (stateless, existing)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/research/multi` | Multi-source parallel gather |
| `POST` | `/api/research/synthesize` | Synthesize existing results (deterministic or Gemini) |
| `POST` | `/api/research/tavily` | Web-only research |
| `POST` | `/api/research/report` | Legacy gather + compile |
| `POST` | `/api/research/export/markdown` | Markdown export |
| `POST` | `/api/research/export/html` | HTML export (browser print → PDF) |
| `POST` | `/api/research/export/json` | JSON export |
| `POST` | `/api/research/chat` | Follow-up chat on existing research |
| `POST` | `/api/research/expand` | Expand research with additional sources |
| `POST` | `/api/research/plan` | Generate action plan from research |

### Session (checkpointed, human-in-the-loop)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/session/start` | Start a session (runs initial gather) |
| `POST` | `/api/session/{id}/message` | Chat turn — may pause for approval |
| `POST` | `/api/session/{id}/decision` | Resume paused turn (accept/decline) |

### Investigation (Director pipeline)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/investigation/runs` | Sync investigation — plan, findings, evidence, cited report (`use_llm` optional) |
| `POST` | `/api/investigation/runs/stream` | Same run over **SSE** (`accepted` → `progress`/`node` → `complete`) |
| `GET` | `/api/investigation/runs/{run_id}` | Fetch stored run status/result (Postgres or memory) |

### MCP

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/mcp/capabilities` | Discover first-party MCP servers + tools |
| `GET` | `/api/mcp/stats` | Process MCP tool-call counts |

### Health

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Process health + `checkpointer` / `investigation_store` / `mcp` |
| `GET` | `/api/health/research` | Graph / source status |

---

## Source Providers

| Source | Client | Auth | Purpose |
|---|---|---|---|
| **Web** | Tavily (`tavily-python`) | `TAVILY_API_KEY` (required) | Articles, docs, blog posts |
| **News** | Google News RSS | None | Current developments |
| **Papers** | Semantic Scholar, OpenAlex, Crossref, arXiv | Optional `SEMANTIC_SCHOLAR_API_KEY` | Academic papers, citations |
| **GitHub** | GitHub Search API | Optional `GITHUB_TOKEN` | Repos, activity, implementation maturity |

Investigation specialists call these providers through **first-party MCP servers** (`USE_MCP=true` by default): Research, Academic, Repository. Set `USE_MCP=false` to fall back to direct LangChain tools.
---

## Research Modes

| Mode | Description | Typical Specialists |
|---|---|---|
| **Explore** | General investigation | Web, optional others |
| **Compare** | Compare approaches/technologies | Web, Papers |
| **Evaluate** | Evaluate production readiness | Web, Repository |
| **Academic** | Research-paper-oriented | Academic, Web |

The Director selects which specialists are needed per question; modes influence the plan but don't hardcode sources.

---

## Schemas

| Schema | File | Purpose |
|---|---|---|
| `InvestigationPlan` | `schemas/investigation.py` | Director's bounded research plan (sub-questions, specialists, budgets) |
| `SubQuestion` | `schemas/investigation.py` | Individual sub-question with assigned specialist |
| `DirectorRequest/Response` | `schemas/investigation.py` | API request/response for investigation runs |
| `SessionStartRequest/Response` | `schemas/session.py` | Session lifecycle types |
| `SessionTurnResponse` | `schemas/session.py` | Chat turn result (`status: answered \| paused`) |
| `InterruptPayload` | `schemas/session.py` | Human-in-the-loop approval payload |
| `MultiSourceResearchResult` | `schemas/research.py` | Parallel gather results |
| `ResearchReport` | `schemas/research.py` | Synthesized report with sections |

---

## Backend Structure

```
backend/
├── app/
│   ├── main.py                     # FastAPI app, router wiring
│   ├── config.py                   # Settings, LLM factory
│   │
│   ├── agents/
│   │   └── director.py             # Research Director (Gemini structured output)
│   │
│   ├── api/
│   │   ├── research.py             # Stateless research endpoints
│   │   ├── session.py              # Checkpointed session endpoints
│   │   └── investigation.py        # Investigation pipeline endpoints
│   │
│   ├── graphs/
│   │   ├── research_graph.py       # Parallel source gather graph
│   │   ├── session_graph.py        # Multi-turn session graph with interrupt()
│   │   ├── investigation_graph.py  # Director → (Specialists) pipeline graph
│   │   └── tavily_graph.py         # Single-source web graph
│   │
│   ├── schemas/
│   │   ├── research.py             # Research types (results, reports, items)
│   │   ├── session.py              # Session/interrupt types
│   │   └── investigation.py        # InvestigationPlan, SubQuestion, budgets
│   │
│   ├── services/
│   │   ├── tavily_client.py        # Web search via Tavily
│   │   ├── news_client.py          # Google News RSS
│   │   ├── papers_client.py        # Semantic Scholar / OpenAlex / Crossref / arXiv
│   │   ├── github_client.py        # GitHub Search API
│   │   ├── report_synthesizer.py   # Deterministic + Gemini report synthesis
│   │   ├── report_export.py        # Markdown / HTML / JSON export
│   │   ├── research_cache.py       # Disk cache (24h TTL)
│   │   ├── research_categories.py  # Category → source mapping
│   │   ├── research_chat.py        # Follow-up chat logic
│   │   ├── topic_router.py         # Intent-based source routing
│   │   └── plan_synthesizer.py     # Action plan generation
│   │
│   └── tools/
│       └── tavily.py               # @tool for future agent use
│
├── tests/
│   ├── test_director.py            # 11 tests: budgets, fallback, truncation
│   └── test_investigation_api.py   # 4 tests: API + regression checks
│
├── requirements.txt
└── pytest.ini
```

## Frontend Structure

Simple flow: **search → loading → answer + sources**.

| Route | Purpose |
|---|---|
| `/` | Search home |
| `/commission` | Same search (alias) |
| `/investigate` | Loading screen, then answer + sources |

API base: `NEXT_PUBLIC_API_URL` (default `http://localhost:8001`).

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI, Uvicorn, Pydantic |
| **Orchestration** | LangGraph (>=1.2.9), LangChain Core |
| **AI** | Google Gemini (`langchain-google-genai`), structured output |
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS v4, IBM Plex |
| **Typography** | Bodoni Moda (display), Instrument Sans (body) |
| **Testing** | pytest, pytest-asyncio |
| **Infrastructure** | Docker Compose (optional), disk cache, python-dotenv |

---

## Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

| Variable | Required | Purpose |
|---|---|---|
| `TAVILY_API_KEY` | Yes | Web search (Tavily) |
| `GOOGLE_API_KEY` | For AI features | Gemini synthesis + Director planning |
| `GEMINI_MODEL` | No | Default `gemini-2.5-flash` |
| `GITHUB_TOKEN` | No | Higher GitHub API rate limit |
| `SEMANTIC_SCHOLAR_API_KEY` | No | Higher Semantic Scholar rate limit |
| `RESEARCH_CACHE_ENABLED` | No | Default `true` |
| `RESEARCH_CACHE_TTL_SECONDS` | No | Default `86400` (24h) |
| `DATABASE_URL` | No | PostgreSQL for LangGraph checkpoints + investigation runs |
| `LANGGRAPH_CHECKPOINT` | No | `auto` (default) \| `postgres` \| `memory` |
| `INVESTIGATION_STORE` | No | `auto` (default) \| `postgres` \| `memory` |
| `USE_MCP` | No | `true` (default) — specialists use MCP tools |

---

## Testing

```bash
cd backend
.venv/bin/python -m pytest -v
```

15 tests covering the Director agent and investigation API. Tests mock the LLM so they run without `GOOGLE_API_KEY`. One optional live test (`test_create_research_plan_live`) runs only when the key is configured.

---

## Design Principles

1. **Agents must perform real reasoning** — not renamed functions or wrappers
2. **Budgets are deterministic** — depth sets task/tool limits, never the LLM
3. **Additive architecture** — new capabilities mount alongside existing ones
4. **Evidence over summaries** — traceable claims backed by cited sources
5. **Minimal LLM usage** — deterministic processing wherever possible
6. **Bounded execution** — no unbounded autonomous loops
7. **Fail gracefully** — every agent has a deterministic fallback

---

## Roadmap

### Completed

- [x] **Parallel source gather** — LangGraph graph with Tavily, News, Papers, GitHub
- [x] **Deterministic report compiler** — structured reports without LLM
- [x] **Optional Gemini synthesis** — one controlled AI call
- [x] **Disk cache** — 24h TTL, category-aware
- [x] **Checkpointed session graph** — multi-turn chat with `interrupt()` human-in-the-loop
- [x] **Research Director agent** — Gemini structured output → InvestigationPlan
- [x] **Investigation graph** — checkpointed pipeline (Director → Specialists)
- [x] **Pytest infrastructure** — Director, specialists, graph, and API tests
- [x] **Web Specialist Agent** — Tavily Search + news tools, bounded tool-calling loop
- [x] **Academic Specialist Agent** — reuses `papers_client.py`, real tool selection
- [x] **Repository Specialist Agent** — reuses `github_client.py`, repo health signals
- [x] **Specialist dispatch** — parallel fan-out after Director with budget split
- [x] **Evidence Analyst** — CLAIM IDs, strength/agreement, conflicts, gaps
- [x] **Synthesis + citation validation** — cited report; invented IDs rejected
- [x] **SSE investigation stream** — `POST /runs/stream` + `GET /runs/{id}`
- [x] **Optional LLM polish** — `use_llm` on investigation runs (default off)
- [x] **Failure isolation + observability** — specialist/evidence/synthesis fallbacks + richer events
- [x] **PostgreSQL checkpointer + durable run store** — auto-fallback to memory when DB is down
- [x] **MCP capability layer** — Research / Academic / Repository servers + specialist scoping

### In Progress

### Planned

- [ ] Critic + bounded gap-fill (V2)
- [ ] Evaluation benchmark

### Completed (frontend)

- [x] **Technical Intelligence Observatory UI** — landing, commission, live SSE observatory, evidence workspace, technical memo report


---

## Cost Philosophy

```
               COST
                │
      ┌─────────┴─────────┐
      │                    │
 Deterministic           AI
  Processing          Processing
      │                    │
      ▼                    ▼
 Most operations       Only when
  happen here         necessary
```

Atelier measures intelligence by **research quality per API call**, not by the number of LLM calls. Budgets are enforced at the graph level — depth controls how many sub-questions the Director creates and how many tool calls specialists are allowed, regardless of what the LLM requests.
