# Atelier — Research Desk

Atelier is a **cost-efficient, multi-source research desk** that turns a research question into ranked sources, structured findings, evidence, comparisons, disagreements, and a cited report.

The goal is **not to build another Perplexity clone** and not to make every step AI-driven. Atelier uses deterministic code wherever possible and uses Gemini only where language understanding or synthesis provides clear value.

The product UI is a paper-and-ink editorial desk (Bodoni Moda + Instrument Sans). The repo folder is still named *AI Social Media Manager*; the running app is Atelier.

| | URL |
|---|---|
| App | `http://localhost:3000` |
| API | `http://localhost:8001` |
| OpenAPI | `http://localhost:8001/docs` |

---

## Product Direction

Atelier should answer:

> **"Help me investigate this question and understand the evidence."**

It should not try to answer:

> "Search the entire internet for me like Perplexity."

The product focuses on **structured research workflows** rather than unrestricted conversational search.

### Core principles

1. **Research-first, not chatbot-first**
2. **Evidence over generic summaries**
3. **Deterministic processing wherever possible**
4. **Minimal LLM usage**
5. **Reuse the sources already retrieved**
6. **Transparent source quality and citations**
7. **Different research modes for different questions**
8. **Avoid unnecessary API calls and uncontrolled agent loops**

---

# What Atelier Does

A user enters a research question and selects a research mode.

Atelier then:

1. Understands the research intent.
2. Selects the most relevant sources.
3. Searches those sources in parallel.
4. Normalizes and deduplicates results.
5. Scores and ranks sources.
6. Builds an evidence layer from the retrieved results.
7. Uses Gemini **only when needed** to synthesize higher-level findings.
8. Produces a structured, cited research report.
9. Lets the user inspect the evidence behind important findings.
10. Allows export to Markdown, JSON, HTML, and printable PDF.

The system should avoid repeated LLM calls for every source.

### What ships today vs this direction

The running app already gathers **web, news, papers, and GitHub in parallel**, caches results, compiles a cited report without an LLM, and optionally rewrites that report with **one Gemini call**.

It does **not** yet have research modes, intent routing, unified quality scores, an evidence layer, or consensus/disagreement sections. Those are the planned phases below. Persona chips (General, AI Engineer, Founder, Academic, News desk) still pick which sources run.

There are **no user accounts** and **no saved history**. The current run lives in React state. A **disk cache** only reuses the same topic so paid APIs are not hit twice.

---

# Research Modes

Instead of making every query an autonomous AI research task, Atelier uses explicit research modes.

## Explore

For general investigation.

Example:

> What are the current approaches to AI agents?

Output:

- Key findings
- Important sources
- Evidence
- Source quality
- Open questions
- Conclusion

---

## Compare

For comparing two or more approaches.

Example:

> RAG vs long-context models for enterprise search

Output:

- Comparison criteria
- Evidence for each side
- Advantages
- Disadvantages
- Use cases
- Trade-offs
- Evidence-backed conclusion

---

## Evaluate

For evaluating a technology, product, architecture, or approach.

Example:

> Is LangGraph suitable for production AI agents?

Output:

- Evaluation criteria
- Evidence
- Strengths
- Weaknesses
- Practical considerations
- Overall assessment

---

## Academic

For research-paper-oriented investigation.

Example:

> Recent research on multimodal RAG

Prioritizes:

- Academic papers
- Research metadata
- Methods
- Results
- Limitations
- Research gaps
- Related work

---

## News / Current Developments

For recent developments.

Prioritizes:

- News
- Current web sources
- Recent publication dates
- Source recency

---

# High-Level Architecture

Atelier uses a **hybrid deterministic + lightweight AI architecture**.

```text
                    USER
                     |
                     v
             Research Question
                     |
                     v
              Research Intent
                     |
                     v
              Source Router
                     |
          +----------+----------+
          |          |          |
          v          v          v
        Tavily     Papers     GitHub
          |          |          |
          +----------+----------+
                     |
                     v
                Gather
                     |
                     v
              Normalize Data
                     |
                     v
             Deduplicate Results
                     |
                     v
              Rank / Score
                     |
                     v
             Evidence Layer
                     |
                     v
        +------------------------+
        | Gemini Synthesis        |
        | ONE controlled call    |
        | when AI is enabled     |
        +-----------+------------+
                    |
        +-----------+-----------+
        |           |           |
        v           v           v
     Findings   Disagreement   Gaps
        |           |           |
        +-----------+-----------+
                    |
                    v
              Final Report
```

The important design decision is:

> **Do not create an autonomous multi-agent loop unless it is clearly required.**

---

# LangGraph

LangGraph remains the orchestration layer.

However, Atelier does **not** use LangGraph as a large autonomous agent system.

## Current role

LangGraph handles:

- Parallel source execution
- Shared research state
- Conditional routing
- Error handling
- Future checkpointing
- Research workflow orchestration

**Today’s graph** (`backend/app/graphs/research_graph.py`):

```text
START
  |
  +----> Tavily Research
  |
  +----> News Research
  |
  +----> Papers Research
  |
  +----> GitHub Research
  |
  v
Gather
  |
  v
Synthesize Report   (skipped when with_report=False)
  |
  v
END
```

Source nodes run in parallel. A node whose source is not in `state["sources"]` returns empty lists and does not call the API. The graph does **not** infer domain from the topic; the studio chip decides.

HTTP flow today:

```text
Studio (topic + category + depth)
        │  POST /api/research/multi
        ▼
cache hit? → return JSON
        ▼
LangGraph invoke  (with_report=False)
        ▼
JSON → React result

Later: POST /api/research/synthesize  (does not re-run the graph)
Later: POST /api/research/export/*    (format the report only)
```

## Planned graph

```text
START
  |
  v
Research Intent
  |
  v
Source Router
  |
  +----> Tavily Research
  |
  +----> News Research
  |
  +----> Papers Research
  |
  +----> GitHub Research
  |
  v
Gather
  |
  v
Normalize + Deduplicate
  |
  v
Rank Sources
  |
  v
Build Evidence
  |
  v
Synthesize Report
  |
  v
END
```

There is a second graph, `tavily_graph.py`: `START → tavily_research → END`, used by `POST /api/research/tavily`.

**What LangGraph is not doing**

- No `bind_tools` / `ToolNode`
- No message loop (agent → tools → agent)
- The LLM does not choose GitHub vs news from the topic

That unused path exists as `backend/app/tools/tavily.py` (`@tool tavily_search`) for a later agent. It should **not** be wired into a ReAct loop unless there is a clear product reason.

---

# Why We Are NOT Building a Full Agent Loop

A full ReAct-style system could repeatedly do:

```text
Gemini
  -> generate query
  -> Tavily
  -> inspect results
  -> generate another query
  -> Tavily
  -> inspect results
  -> search again
  -> Gemini
  -> verify
  -> search again
```

This is intentionally avoided.

Reasons:

- Higher API cost
- Less predictable latency
- Harder debugging
- Harder caching
- More failure points
- Possible infinite or unnecessary research loops
- The current sources already provide enough information for many research tasks

Atelier should use AI **surgically**, not everywhere.

---

# Lightweight AI Strategy

Gemini should primarily be used for:

### 1. Research intent interpretation

Convert the user's request into a structured intent.

Example:

```json
{
  "mode": "compare",
  "topic": "RAG vs long-context models",
  "source_types": ["web", "papers", "github"],
  "focus": [
    "accuracy",
    "latency",
    "cost",
    "enterprise_use"
  ]
}
```

This should be one small structured call.

---

### 2. Report synthesis

Gemini receives the already retrieved and processed sources and creates:

- Key findings
- Consensus
- Disagreements
- Open questions
- Conclusion

It should **not** independently perform additional web research.

---

### 3. Optional AI enhancement

The existing `use_llm` option remains available.

If disabled:

```text
Sources
  -> deterministic compilation
  -> structured report
```

If enabled:

```text
Sources
  -> Gemini synthesis
  -> structured report
```

If Gemini fails, the deterministic compiler remains the fallback.

---

# Cost-Control Rules

Cost control is a first-class product requirement.

## Rule 1: Do not call Gemini per source

Bad:

```text
10 sources
  -> 10 Gemini calls
```

Preferred:

```text
10-30 sources
  -> preprocessing
  -> 1 Gemini synthesis call
```

---

## Rule 2: Do not repeatedly search the same topic

Use the existing disk cache.

```text
Topic + Mode + Sources
        |
        v
24-hour cache
```

A cache hit should avoid paid APIs whenever possible.

Today the cache key includes topic, limit, **category**, and sources (`v5-categories`). When research modes land, the key should include **mode** instead of category.

---

## Rule 3: Prefer deterministic processing

Use Python for:

- Deduplication
- URL normalization
- Date extraction
- Recency scoring
- Domain/source classification
- Metadata processing
- Basic relevance scoring
- Ranking
- Filtering
- Source grouping
- Citation formatting

Do not use an LLM for tasks that ordinary code can reliably perform.

---

## Rule 4: Fixed research budgets

Every research mode should have a controlled source limit.

Example:

| Mode | Target sources | AI usage |
|---|---:|---|
| Explore | 10-15 | Optional 1 call |
| Compare | 15-25 | 1 call |
| Evaluate | 15-25 | 1 call |
| Academic | 15-30 | 1 call |
| News | 10-20 | 1 call |

These are starting defaults and should remain configurable.

---

# Source Router

The current category system is replaced by a more useful **research intent + source routing** approach.

The router determines which existing source clients should run.

| Research mode | Web | News | Papers | GitHub |
|---|---:|---:|---:|---:|
| Explore | ✓ | Optional | Optional | Optional |
| Compare | ✓ | Optional | ✓ | Optional |
| Evaluate | ✓ | Optional | ✓ | ✓ |
| Academic | ✓ | No | ✓ | Optional |
| News | ✓ | ✓ | No | No |

The router does not need to be fully autonomous.

Rules can handle most routing, with Gemini used only when the request is ambiguous.

### Current category presets

Until modes ship, `research_categories.py` maps chips to sources:

| Category | Sources |
|---|---|
| General / Founder | web, news, papers |
| AI Engineer | web, papers, GitHub |
| Academic | papers, web |
| News desk | news, web |

---

# Source Quality Scoring

Every source should receive a transparent score.

The score should primarily be calculated without an LLM.

Possible factors:

```text
Source Score
|
+-- Relevance
+-- Authority
+-- Recency
+-- Source type
+-- Evidence availability
+-- Publication quality
```

Example:

| Factor | Weight |
|---|---:|
| Relevance | 35% |
| Authority | 25% |
| Recency | 20% |
| Source quality | 20% |

Weights should be configurable by research mode.

For example, Academic mode can increase the importance of academic authority and publication metadata.

Today, ranking uses Tavily relevance, citation counts, and GitHub stars — not this unified score.

---

# Source Types

Atelier currently uses:

## Live Web

Client:

`tavily-python` / `httpx`

Purpose:

- Technical articles
- Documentation
- Industry analysis
- General web research

Authentication:

`TAVILY_API_KEY`

---

## News

Client:

Google News RSS

Purpose:

- Recent developments
- Announcements
- Current events

Authentication:

None

---

## Academic Papers

Sources:

- Semantic Scholar
- OpenAlex
- Crossref
- arXiv

Purpose:

- Research papers
- Academic metadata
- Literature discovery
- Research trends

Semantic Scholar API key is optional.

---

## GitHub

Client:

GitHub Search API

Purpose:

- Open-source implementations
- Libraries
- Repositories
- Project activity

`GITHUB_TOKEN` is optional and provides a higher rate limit.

---

# Evidence Layer

This is one of the most important additions to Atelier.

Instead of treating search results as the final data model, Atelier creates a lightweight evidence representation.

Example:

```text
Claim
  |
  +-- Supporting sources
  +-- Source type
  +-- Publication date
  +-- Relevant passage / metadata
  +-- Evidence strength
```

The evidence layer should be generated primarily from the existing retrieved results.

It should not trigger another search.

---

# Evidence Classification

Sources and findings can be classified as:

- Primary evidence
- Academic evidence
- Implementation evidence
- Secondary analysis
- News report
- Opinion

Example:

```text
🟢 Primary / academic evidence
🔵 Technical analysis
🟡 Opinion / commentary
⚪ News coverage
```

This helps users understand what type of evidence supports a finding.

---

# Consensus and Disagreement

A major research feature is distinguishing:

### Consensus

What multiple independent sources broadly agree on.

### Disagreement

Where credible sources reach different conclusions.

### Unclear

Where evidence is insufficient.

The final report can contain:

```text
Consensus
...

Disagreements
...

Why the disagreement may exist
...

Evidence strength
...
```

This uses the already retrieved source set.

The preferred implementation is **one Gemini synthesis call**, not a separate fact-checking agent.

---

# Source Independence

Multiple websites may repeat the same original claim.

Atelier should try to identify duplicate or closely related sources.

Example:

```text
12 sources mention Claim A

But:

8 appear to originate from the same announcement.
```

The UI should avoid treating those 8 sources as 8 independent pieces of evidence.

Initial implementation can use deterministic similarity and URL/domain metadata.

More advanced semantic clustering can be added later if needed.

---

# Research Gaps

Academic and research-heavy modes should identify:

- Missing evidence
- Under-researched areas
- Conflicting findings
- Areas with limited recent research
- Questions that remain unresolved

This should be generated from the retrieved source set rather than launching a new autonomous research process.

Example:

```text
Research Gaps

1. Limited post-2025 comparison between X and Y.
2. Most benchmarks use the same dataset.
3. Production latency is poorly studied.
4. Security implications remain underexplored.
```

---

# Research Report Structure

Reports should become more structured.

## Explore

```text
Research Question

Executive Summary

Key Findings

Evidence

Source Quality

Consensus

Disagreements

Open Questions

Conclusion

Sources
```

## Compare

```text
Research Question

Comparison Criteria

Option A

Option B

Evidence Comparison

Trade-offs

Best Use Cases

Conclusion

Sources
```

## Evaluate

```text
Research Question

Evaluation Criteria

Evidence

Strengths

Weaknesses

Risks

Practical Considerations

Overall Assessment

Sources
```

## Academic

```text
Research Question

Research Landscape

Key Papers

Methods

Findings

Limitations

Consensus

Research Gaps

Open Questions

References
```

**Current report** (one template for all runs): source mix, executive summary, key findings, news highlights, academic context, open questions, sources.

---

# "Why This Source?"

Every important result should expose why it was ranked highly.

Example:

```text
Why this source?

Relevance     94
Authority     88
Recency       97
Evidence      91
```

The scores should come from deterministic scoring where possible.

---

# "Follow the Evidence"

Important report findings should be traceable to their sources.

A user should be able to move from:

```text
Finding
  ↓
Supporting source
  ↓
Relevant evidence
  ↓
Original page / paper / repository
```

The report should never hide where an important conclusion came from.

---

# Research Follow-up

A lightweight follow-up experience can be added later.

Examples:

- "Show me the evidence against this conclusion."
- "Only show papers after 2025."
- "Compare the strongest two approaches."
- "Which claims have weak evidence?"
- "Show me the primary sources."

The follow-up system should reuse the existing research state whenever possible rather than performing a completely new research run.

---

# PostgreSQL

PostgreSQL currently exists in `docker-compose.yml` but is not used by the application.

The database can eventually store:

```text
Research Session
    |
    +-- Research Question
    +-- Research Mode
    +-- Queries
    +-- Sources
    +-- Evidence
    +-- Claims
    +-- Report
```

Persistence is useful for:

- Research history
- Re-opening reports
- Comparing research sessions
- Follow-up questions
- Future research tracking

Database persistence is **not required for the first lightweight version**.

---

# LangGraph Checkpointing

Checkpointing can be introduced once research sessions become persistent.

Potential use:

```text
Web ✓
Papers ✓
GitHub ✓
News ✗
   |
   v
Resume only failed/incomplete work
```

This avoids rerunning completed work.

Checkpointing is a later-stage reliability feature, not a requirement for the initial MVP.

---

# Future Research Tracking

A future feature can allow users to save a research topic and later see:

```text
What changed?

New sources
New papers
New findings
Changed consensus
New GitHub activity
New developments
```

This should be built only after persistence is implemented.

---

# Caching

Current cache:

`backend/.cache/research/`

Default TTL:

`24 hours`

Cache key includes:

- Topic
- Limit
- Category/mode
- Sources

The cache should continue to be used aggressively.

UI **Refresh** sends `force_refresh: true`. This is **not** per-user history. Anyone with the same topic hits the same file.

Potential future cache improvements:

- Cache individual source results
- Cache normalized results
- Cache source metadata
- Avoid repeating unchanged searches

---

# Error Handling

Each source should fail independently.

Example:

```text
Tavily       ✓
News         ✓
Papers       ✗
GitHub       ✓
```

The research should still complete.

Errors should be stored in shared state:

```python
errors: dict
```

and displayed clearly in the UI. Parallel LangGraph nodes merge errors with `Annotated[dict, _merge_dicts]` so two failing sources both keep their messages.

---

# Frontend

Current stack remains:

| Piece | Role |
|---|---|
| Next.js 16 | App Router / frontend |
| React 19 | UI |
| TypeScript | Types |
| Tailwind v4 | Styling |
| Bodoni Moda | Editorial display font |
| Instrument Sans | Body font |

The browser talks to the API with `fetch` to `http://localhost:8001`. No Next.js API routes for research. The product UI lives in `frontend/src/app/page.tsx` (studio, loader, results) and `frontend/src/components/HeroHome.tsx` (landing).

Potential UI additions:

### Research mode selector

```text
Explore | Compare | Evaluate | Academic | News
```

### Research depth

```text
Quick | Standard | Deep
```

For the initial version, Deep should still have a **fixed source/API budget**, not an unlimited autonomous loop.

### Evidence indicators

Show:

- Source type
- Quality score
- Recency
- Evidence strength

### Research sections

Tabs can evolve toward:

```text
Overview
Evidence
Sources
Papers
GitHub
News
Disagreements
Research Gaps
```

Only show sections relevant to the selected research mode.

---

# API

Existing endpoints:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Process health |
| GET | `/api/health/research` | Graph / category / source status |
| POST | `/api/research/tavily` | Web-only research |
| POST | `/api/research/multi` | Multi-source research |
| POST | `/api/research/synthesize` | Synthesize existing results |
| POST | `/api/research/report` | Legacy gather + compile |
| POST | `/api/research/export/markdown` | Markdown export |
| POST | `/api/research/export/html` | HTML export |
| POST | `/api/research/export/json` | JSON export |

`POST /api/research/multi` body today: `{ topic, limit, category, force_refresh? }`.

`POST /api/research/synthesize` sends the sources already on screen. Default is a **deterministic compile**. `use_llm: true` → Gemini `with_structured_output(ResearchReport)`. On LLM failure it falls back to compile.

HTML export is meant for the browser print dialog (Save as PDF).

Future endpoints may include:

```text
POST /api/research/plan
POST /api/research/follow-up
GET  /api/research/{id}
```

but these should only be added when their underlying functionality is implemented.

---

# Backend Repository Map

```text
backend/app/
  main.py
  config.py

  api/
    research.py

  graphs/
    research_graph.py
    tavily_graph.py

  schemas/
    research.py

  services/
    tavily_client.py
    news_client.py
    papers_client.py
    github_client.py
    preview_client.py
    report_synthesizer.py
    report_export.py
    research_cache.py
    research_categories.py

  tools/
    tavily.py

  # Future lightweight research modules
  services/
    research_router.py
    source_ranker.py
    evidence_builder.py
```

```text
frontend/src/
  app/page.tsx            Studio, loader, results, API calls
  app/layout.tsx          Fonts, metadata
  components/HeroHome.tsx Landing page
  lib/reportDownload.ts   Export helpers
```

---

# Recommended Implementation Order

## Phase 1 — Current Foundation

Keep:

- Tavily
- Google News RSS
- Semantic Scholar
- OpenAlex
- Crossref
- arXiv
- GitHub
- LangGraph parallel execution
- Disk cache
- Deterministic report compiler
- Optional Gemini synthesis

---

## Phase 2 — Research Intelligence Without Large AI Costs

Build:

1. Research modes
2. Intent-based source routing
3. Source quality scoring
4. Better ranking
5. Deduplication
6. Evidence layer
7. Evidence/source classification
8. Structured report templates
9. Consensus/disagreement section
10. Research gaps section

Most of this should be deterministic.

---

## Phase 3 — Minimal Gemini Layer

Use Gemini for only:

1. Ambiguous research-intent classification
2. One structured synthesis call

Avoid:

- LLM per source
- LLM per query
- LLM fact checker
- LLM critic
- Autonomous research loops

---

## Phase 4 — Persistence

Introduce PostgreSQL for:

- Research sessions
- Saved reports
- Sources
- Evidence
- Claims
- Research history

---

## Phase 5 — Advanced Research Workspace

Only after the core product works:

- Follow-up research
- LangGraph checkpointing
- Research history
- Citation graph
- Research tracking
- "What changed?" research
- Saved research projects

---

# Cost Philosophy

Atelier should follow this architecture:

```text
                 COST
                  |
        +---------+---------+
        |                   |
   Deterministic         AI
    Processing         Processing
        |                   |
        v                   v
   Most operations      Only when
   happen here         necessary
```

The product should **not** measure intelligence by the number of LLM calls.

The goal is:

> **Maximum research quality per API call.**

---

# Current Technology Stack

## Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS v4
- Bodoni Moda
- Instrument Sans

## Backend

- FastAPI
- Uvicorn
- Pydantic
- LangGraph
- LangChain
- `langchain-google-genai`

## AI

- Google Gemini
- Optional structured synthesis

## Search / Research

- Tavily
- Google News RSS
- Semantic Scholar
- OpenAlex
- Crossref
- arXiv
- GitHub Search API

## Infrastructure

- PostgreSQL planned
- Docker Compose
- Disk cache
- Python dotenv

---

# Environment

Copy `.env.example` to `.env` at the repository root.

```env
TAVILY_API_KEY=
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GITHUB_TOKEN=
RESEARCH_CACHE_ENABLED=true
RESEARCH_CACHE_TTL_SECONDS=86400
DATABASE_URL=
```

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

# Local Development

```bash
cp .env.example .env

cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd ..

cd frontend
npm install
cd ..

./run.sh
```

`run.sh` starts Uvicorn `:8001` and Next `:3000`, both with reload. Ctrl+C stops both.

The application runs:

```text
Frontend → http://localhost:3000
Backend  → http://localhost:8001
OpenAPI  → http://localhost:8001/docs
```

Docker Compose can start `db` + `backend` + `frontend`, but Postgres is unused until persistence is built.

---

# Product Boundary

Atelier is intentionally **not**:

- A general-purpose chatbot
- A fully autonomous browser agent
- An unlimited deep-research engine
- A Perplexity replacement
- A multi-agent framework demonstration

Atelier is:

> **A lightweight, evidence-oriented research desk that combines multiple research sources, deterministic analysis, and carefully controlled AI synthesis.**

The core advantage should be **research structure, evidence traceability, source quality, and useful synthesis**, while keeping API usage and infrastructure costs low.
