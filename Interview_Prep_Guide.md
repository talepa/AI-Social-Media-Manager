# AI Social Media Manager: Interview Prep & Concept Guide

This document captures all the core concepts, methods, architectures, and "why" behind the technical decisions made while building the AI Social Media Manager. Use this as an interview preparation resource.

## Module 1: Project Skeleton & Foundation

### Concept 1: Monorepo Structure
**What it is:** A single repository that houses multiple, distinct projects (in our case, the frontend, backend, and infrastructure configuration like Docker).
**Why use it here?**
- **Simplified Local Development:** Using `docker-compose`, we can spin up the frontend, backend, and database with a single command.
- **Unified Versioning:** A single commit can capture changes across the entire stack, ensuring frontend and backend stay in sync.
- **Easy Onboarding:** New developers just clone one repo and run one command to get started.

### Concept 2: FastAPI for the Backend
**What it is:** A modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints.
**Why use it here?**
- **Speed & Async:** FastAPI natively supports asynchronous programming (`async`/`await`), which is critical for an AI application that will spend a lot of time waiting on external LLM APIs (like OpenAI or Anthropic).
- **Pydantic Validation:** It uses Pydantic for data validation out of the box, which aligns perfectly with our need for structured LLM outputs.
- **Auto-Documentation:** Generates OpenAPI (Swagger) documentation automatically, making it easy to test endpoints.

### Concept 3: Next.js + TypeScript for the Frontend
**What it is:** A React framework that provides building blocks to create fast web applications, coupled with a strongly typed language (TypeScript).
**Why use it here?**
- **TypeScript:** Enforces type safety, catching errors at compile time rather than runtime. This is crucial for maintaining a complex application.
- **Server/Client Components:** Next.js App Router allows us to mix server-rendered and client-rendered components, optimizing performance.

### Concept 4: Docker & Docker Compose
**What it is:** Docker packages applications and their dependencies into standardized units called containers. Docker Compose is a tool for defining and running multi-container Docker applications.
**Why use it here?**
- **"Works on my machine" problem solved:** Ensures that the app runs exactly the same way in development, testing, and production.
- **PostgreSQL Setup:** We can easily spin up a robust database without needing to manually install it on our host operating system.

### Code Snippet & Solution: Backend `/health` Endpoint
**Question:** How do you implement a basic health check in FastAPI?
**Answer:**
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Health check endpoint to verify the service is running.
    """
    return {"status": "ok", "service": "AI Social Media Manager Backend"}
```
**Why:** A health check endpoint is essential for monitoring the application's uptime. In a containerized environment (like Docker or Kubernetes), orchestrators use this endpoint to know if the container is healthy or needs to be restarted.

## Module 2: Backend Clean Architecture

### Concept 1: Separation of Concerns
**What it is:** Organizing the codebase so each part has a distinct responsibility (e.g., `api/` for routing, `services/` for business logic, `database/` for persistence).
**Why use it here?**
- Makes the codebase scalable and maintainable.
- Easier to test individual components (e.g., mocking the database layer while testing services).

### Concept 2: Pydantic Schemas vs. ORM Models
**What it is:** We separate data structures used for API validation (Pydantic in `schemas/`) from those used for database mapping (SQLAlchemy/SQLModel in `database/`).
**Why use it here?**
- Prevents accidental exposure of sensitive database fields to the client.
- Distinctly separates validation logic from storage logic.

## Module 3: LangGraph Foundation

### Concept 1: LangGraph vs. LangChain
**What it is:** LangChain is a framework for building LLM applications (chains, prompt templates, tool calling). LangGraph is built on top of LangChain specifically to handle cyclic graphs (loops) and stateful, multi-actor applications.
**Why use it here?**
- Social Media management requires complex agent workflows (e.g., Reviewer agent rejecting a post and sending it back to the Writer). Standard linear chains cannot handle these loops easily.

### Concept 2: State (AgentState)
**What it is:** A TypedDict that defines the schema of the data passed between nodes in the graph.
**Why use it here?**
- Ensures all nodes receive the same structured context (like conversation history, current task, metadata).
- Using `Annotated` with `operator.add` allows nodes to append to lists (like appending a new message) rather than overwriting the entire state.

### Concept 3: Nodes and Edges
**What it is:** 
- **Nodes:** Python functions representing actors or actions (e.g., a "Writer Node" calling an LLM). They take the State, perform work, and return state updates.
- **Edges:** The wiring that connects nodes, defining the flow of execution. Conditional edges can route execution based on state values (e.g., `if approved, go to Publisher; else, go to Writer`).
**Why use it here?**
- Provides a clear, visualizable, and deterministic flow of control for complex multi-agent interactions.

### Concept 4: Graph Execution (Compile)
**What it is:** Calling `.compile()` turns the defined nodes and edges into an executable LangChain `Runnable`.
**Why use it here?**
- Once compiled, it behaves like any other LangChain object, supporting streaming, async execution, and batch processing out of the box.

## Module 4: Research Agent & Tool Calling

### Concept 1: Tool Abstraction (`@tool`)
**What it is:** Using the `@tool` decorator in LangChain to wrap standard Python functions so that an LLM can understand and invoke them.
**Why use it here?**
- LLMs only know information up to their training cutoff. By wrapping APIs (like Tavily, Google Trends, Reddit, News) as tools, we give the Research Agent live internet access to gather current trends.
- The docstring of the function becomes the instruction manual for the LLM on *when* and *how* to use the tool.

### Concept 2: Structured Output (Pydantic Models)
**What it is:** Forcing the LLM to return its final answer strictly formatted according to a defined Pydantic schema (e.g., `ResearchReport`).
**Why use it here?**
- In an agentic workflow, downstream agents (like the Planner Agent) need predictable, machine-readable data (JSON) rather than free-flowing text.
- `with_structured_output` ensures we get exactly the fields we asked for, preventing parsing errors.
