# Atelier — multi-source research desk

Atelier turns a **topic** into **ranked sources** (web, news, papers, GitHub) and, on demand, a **cited report** you can browse and export.

The product UI is a paper-and-ink editorial desk (Bodoni Moda + Instrument Sans). The repo folder is still named *AI Social Media Manager*; the running app is the research desk.

| | URL |
|---|---|
| App | http://localhost:3000 |
| API | http://localhost:8001 |
| OpenAPI | http://localhost:8001/docs |

---

## What it does

1. You enter a topic and pick a **research type** (General, AI Engineer, Founder, Academic, News desk).
2. The backend runs those sources **in parallel** via LangGraph.
3. The UI shows findings (cards/list), previews, scores, citations, stars.
4. You optionally **generate a report** (fast compile, or Gemini rewrite).
5. You download **Markdown**, **JSON**, or print-to-PDF.

There are **no user accounts** and **no saved history**. The current run lives in React state. Refreshing the page clears it unless you exported. A **disk cache** only reuses the same topic so paid APIs are not hit twice.

---

## Tech stack

### Frontend (`frontend/`)

| Piece | Role |
|---|---|
| Next.js 16 (App Router) | UI, `src/app/page.tsx` is the whole product |
| React 19 | Views: hero → studio → loader → results |
| TypeScript | Types for research payloads |
| Tailwind v4 + `globals.css` | Editorial layout, grain, ink buttons |
| Bodoni Moda + Instrument Sans | Display + body (Google fonts in `layout.tsx`) |

The browser talks to the API with `fetch` to `http://localhost:8001`. No Next.js API routes for research.

### Backend (`backend/`)

| Piece | Role |
|---|---|
| FastAPI + Uvicorn | HTTP API on port **8001** |
| Pydantic | Request/response models (`app/schemas/research.py`) |
| LangGraph | Orchestrates the research **pipeline** (nodes + edges + shared state) |
| LangChain | LLM wrapper + unused `@tool` for Tavily; Gemini structured output for reports |
| `langchain-google-genai` | Gemini (`get_llm()` in `app/config.py`) |
| `tavily-python` / httpx | Web search and other HTTP clients |
| python-dotenv | Loads root `.env` |

### External sources (not LangGraph “tools”)

| Source | Client | Auth |
|---|---|---|
| Live web | Tavily Search | `TAVILY_API_KEY` **required** |
| News | Google News RSS | none |
| Papers | Semantic Scholar, OpenAlex, Crossref, arXiv (parallel) | S2 key optional |
| GitHub repos | GitHub Search API | `GITHUB_TOKEN` optional (higher rate limit) |
| Page previews | Fetch HTML for `og:image` | none |
| Report rewrite | Gemini | `GOOGLE_API_KEY` only if “Enhance with AI” |

### Infra that exists but is unused

`docker-compose.yml` starts **PostgreSQL** and sets `DATABASE_URL`. The Python app **never connects** to it. `psycopg2-binary` is in requirements for that future path. Research is not stored in a database.

---

## Repository map

```text
backend/app/
  main.py                 FastAPI app, CORS, mounts research router
  config.py               Gemini client (get_llm)
  api/research.py         HTTP: multi, synthesize, export, health
  graphs/
    research_graph.py     Main LangGraph (parallel sources → gather → synthesize)
    tavily_graph.py       Tiny graph: START → Tavily → END
  schemas/research.py     ResearchItem, report, multi-source result
  services/
    tavily_client.py      Web search
    news_client.py        Headlines
    papers_client.py      Academic libraries
    github_client.py      Repo search
    preview_client.py     Thumbnails
    report_synthesizer.py Compile report or Gemini enhance
    report_export.py      Markdown / HTML
    research_cache.py     Disk JSON cache (~24h)
    research_categories.py Category → which sources to run
  tools/tavily.py         LangChain @tool wrapper — not used by the graph yet

frontend/src/
  app/page.tsx            Studio, loader, results, API calls
  app/layout.tsx          Fonts, metadata
  components/HeroHome.tsx Landing page
  lib/reportDownload.ts   Export helpers
```

---

## How a request runs (current flow)

```text
Studio (topic + category + depth)
        │  POST /api/research/multi
        ▼
FastAPI  research_multi()
        │  cache hit? → return JSON
        ▼
run_multi_source_research()
        │  resolve_sources(category)
        ▼
LangGraph  research_graph.invoke(state)
        │
        ├─ tavily_research  ─┐
        ├─ news_research     ─┼─ (parallel; disabled sources return [])
        ├─ papers_research   ─┤
        └─ github_research   ─┘
                ▼
              gather          (normalize + og:image + backfill)
                ▼
        synthesize_report     (skipped when with_report=False)
                ▼
JSON → React `result` → tabs (overview / web / news / papers / github)

Later: POST /api/research/synthesize  (does not re-run the graph)
Later: POST /api/research/export/*    (format the report only)
```

### 1. Gather

`POST /api/research/multi`

Body: `{ topic, limit, category, force_refresh? }`

Category presets (`research_categories.py`):

| Category | Sources |
|---|---|
| General / Founder | web, news, papers |
| AI Engineer | web, papers, GitHub |
| Academic | papers, web |
| News desk | news, web |

The graph **always** has four source nodes. A node whose name is not in `state["sources"]` returns empty lists and **does not** call the API. The graph does **not** infer domain from the topic (fashion vs tech). The chip decides.

### 2. Report (separate request)

`POST /api/research/synthesize`

The client sends the sources already on screen. Default is a **deterministic compile** (no LLM): ranked findings, news highlights, academic context, open questions, bibliography.

`use_llm: true` → Gemini `with_structured_output(ResearchReport)`. On LLM failure it falls back to compile.

### 3. Export

`POST /api/research/export/markdown` · `/html` · `/json`

HTML is meant for the browser print dialog (Save as PDF).

---

## LangGraph — how it is used

LangGraph here is a **fixed pipeline**, not a ReAct agent.

- **State** = `MultiSourceState` (TypedDict): topic, limit, category, sources, result lists, media, errors, optional report.
- **Nodes** = Python functions that return a **partial state update**.
- **Edges** = START fans out to four source nodes; all four join at `gather`; then `synthesize_report`; then END.
- **Parallelism** = the four source nodes run together. `gather` waits for all of them.
- **Error merge** = `errors` is `Annotated[dict, _merge_dicts]` so two failing sources both keep their messages.

Entry point:

```python
research_graph.invoke({
    "topic": topic,
    "limit": limit,
    "with_report": False,
    "category": category,
    "sources": ["tavily", "papers", "github"],  # example: AI Engineer
    "errors": {},
})
```

There is a second graph, `tavily_graph.py`: `START → tavily_research → END`, used by `POST /api/research/tavily`.

**What LangGraph is not doing today**

- No `bind_tools` / `ToolNode`
- No message loop (agent → tools → agent)
- The LLM does not choose GitHub vs news from the topic

That unused path exists as `backend/app/tools/tavily.py` (`@tool tavily_search`) for a later agent.

---

## LangChain — how it is used

| Use | Where |
|---|---|
| `ChatGoogleGenerativeAI` | `app/config.py` → `get_llm()` |
| Structured report | `report_synthesizer.py` when `use_llm=True` |
| `@tool` | `app/tools/tavily.py` — **not wired** into the graph |

Gathering sources does **not** go through LangChain. Nodes call `search_web()`, `search_news()`, `search_papers()`, `search_github_repos()` directly.

---

## Cache

`backend/.cache/research/` (gitignored).

- Key includes topic, limit, category, sources (`v5-categories`).
- Default TTL **24 hours** (`RESEARCH_CACHE_TTL_SECONDS`).
- Same topic + category → skip Tavily and other APIs.
- UI **Refresh** sends `force_refresh: true`.
- This is **not** per-user history. Anyone with the same topic hits the same file.

---

## Environment

Copy `.env.example` to `.env` at the **repo root**.

| Variable | Required | Purpose |
|---|---|---|
| `TAVILY_API_KEY` | Yes (web) | Tavily search |
| `GOOGLE_API_KEY` | For AI report | Gemini enhance |
| `GEMINI_MODEL` | No | Default `gemini-2.5-flash` |
| `GITHUB_TOKEN` | No | Higher GitHub Search rate limit |
| `RESEARCH_CACHE_ENABLED` | No | Default on |
| `DATABASE_URL` | No | Compose only; unused by the app |

Never commit `.env`.

---

## Run locally

```bash
cp .env.example .env   # then fill TAVILY_API_KEY

cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd ..
cd frontend && npm install && cd ..

./run.sh
```

`run.sh` starts Uvicorn `:8001` and Next `:3000`, both with reload. Ctrl+C stops both.

Docker Compose can start `db` + `backend` + `frontend`, but Postgres is unused until persistence is built.

---

## API cheat sheet

| Method | Path | What |
|---|---|---|
| GET | `/health` | Process up |
| GET | `/api/health/research` | Graph nodes, categories, sources |
| POST | `/api/research/tavily` | Web only (small graph) |
| POST | `/api/research/multi` | Parallel gather, no report |
| POST | `/api/research/synthesize` | Report from existing sources |
| POST | `/api/research/report` | Legacy: gather + compile |
| POST | `/api/research/export/markdown` | `.md` |
| POST | `/api/research/export/html` | Printable HTML |
| POST | `/api/research/export/json` | Report JSON |

---

## Data: what is stored where

| Data | Stored? |
|---|---|
| Current topic / results / report | Browser memory only |
| Repeat of the same topic | Disk cache ~24h |
| User accounts, past runs | **No** |
| Postgres | Running in Compose if you use it; **app does not write** |

---

## Design notes (so the next change is safe)

- **Category chips** pick sources. The topic string is not classified (a fashion query on “General” still hits papers, not a fashion-only index).
- **LangGraph tools** would be the way to let Gemini choose sources and rewrite queries from the topic. That is not the current graph.
- Adding a source = client in `services/` + node + edge into `gather` + field on `MultiSourceState` / `ResearchItem` + UI tab.
- Do not treat `app/tools/tavily.py` as live until it is bound with `ToolNode`.
