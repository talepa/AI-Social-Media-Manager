"""
Force in-memory backends for the unit suite so a local DATABASE_URL / Docker
Postgres does not change test behavior or leave durable side effects.
"""

from __future__ import annotations

import os

# Must run before app.graphs / investigation_store import get_checkpointer / _build_store.
os.environ["LANGGRAPH_CHECKPOINT"] = "memory"
os.environ["INVESTIGATION_STORE"] = "memory"
