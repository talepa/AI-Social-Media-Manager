# AI Social Media Manager -- Antigravity Master Build Guide

> Build this project **module by module**. Never build the entire
> project at once.

## Global Rules

-   Backend: FastAPI
-   Frontend: Next.js + TypeScript
-   LangGraph + LangChain
-   PostgreSQL
-   Docker
-   Clean Architecture
-   Pydantic models
-   Type hints everywhere
-   Add docstrings.
-   Add comments explaining **why** code exists.
-   Stop after each module.

------------------------------------------------------------------------

## Module 1 -- Project Setup

### Goal

Create the complete project skeleton.

### Tasks

-   Create monorepo.
-   Setup backend.
-   Setup frontend.
-   Configure Docker.
-   Configure PostgreSQL.
-   Create `.env.example`.
-   Add logging.
-   Health endpoint.
-   Home page.

### After completion

Explain every folder created. Do not continue.

------------------------------------------------------------------------

## Module 2 -- Backend Foundation

Create:

-   app/
-   api/
-   agents/
-   graphs/
-   tools/
-   services/
-   memory/
-   database/
-   schemas/

Explain each folder.

Stop.

------------------------------------------------------------------------

## Module 3 -- LangGraph Foundation

Build:

-   StateGraph
-   START
-   END
-   State model
-   Sample node

Explain: - State - Nodes - Edges - Graph execution

Comment complex code.

Stop.

------------------------------------------------------------------------

## Module 4 -- Research Agent

Implement:

-   Tavily tool
-   Google Trends abstraction
-   Reddit abstraction
-   News abstraction

Use tool calling.

Return structured output.

Explain every file.

Stop.

------------------------------------------------------------------------

## Module 5 -- Planner Agent

Transform research into a weekly content plan.

Use Pydantic models.

Return JSON.

Explain validation.

Stop.

------------------------------------------------------------------------

## Module 6 -- Writer Agent

Generate: - LinkedIn post - Instagram caption - Hashtags - CTA

Support brand voice.

Explain prompts.

Stop.

------------------------------------------------------------------------

## Module 7 -- Reviewer Agent

Review: - Grammar - Tone - Brand consistency

Implement conditional routing.

Stop.

------------------------------------------------------------------------

## Module 8 -- Human Approval

Implement LangGraph interrupt.

Pause graph.

Resume after approval.

Create approval UI.

Stop.

------------------------------------------------------------------------

## Module 9 -- Publishing

Create adapter interface:

-   publish_post()
-   schedule_post()
-   get_analytics()
-   reply_comment()

Implement LinkedIn adapter first.

Stop.

------------------------------------------------------------------------

## Module 10 -- Memory

Implement: - Short-term memory - Long-term memory - Checkpointer -
PostgreSQL persistence

Explain architecture.

Stop.

------------------------------------------------------------------------

## Module 11 -- Analytics

Collect engagement metrics.

Persist analytics.

Explain schema.

Stop.

------------------------------------------------------------------------

## Module 12 -- Strategy Agent

Analyze analytics and trends.

Generate next week's strategy.

Stop.

------------------------------------------------------------------------

## Final Module

-   Authentication
-   Docker
-   Deployment
-   README
-   Architecture diagrams
-   Tests

Do not modify previous modules except bug fixes.
