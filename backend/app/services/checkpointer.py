"""
services/checkpointer.py

LangGraph checkpointer selection:
  - Postgres when DATABASE_URL is reachable (durable across restarts)
  - MemorySaver otherwise (dev / no DB)

Env:
  DATABASE_URL=postgresql://...
  LANGGRAPH_CHECKPOINT=auto|postgres|memory   (default: auto)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Literal, Tuple

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

CheckpointKind = Literal["memory", "postgres"]

_pool: Any = None
_checkpointer: Any = None
_kind: CheckpointKind | None = None


def _database_url() -> str:
    return (os.getenv("DATABASE_URL") or "").strip()


def _mode() -> str:
    return (os.getenv("LANGGRAPH_CHECKPOINT") or "auto").strip().lower()


def get_checkpointer() -> Tuple[Any, CheckpointKind]:
    """
    Return (checkpointer, kind). Cached for process lifetime.
    Never raises — always falls back to MemorySaver.
    """
    global _pool, _checkpointer, _kind
    if _checkpointer is not None and _kind is not None:
        return _checkpointer, _kind

    mode = _mode()
    if mode == "memory":
        _checkpointer, _kind = MemorySaver(), "memory"
        logger.info("langgraph checkpointer: MemorySaver (forced)")
        return _checkpointer, _kind

    url = _database_url()
    if mode == "postgres" or (mode == "auto" and url):
        try:
            cp, pool = _build_postgres(url)
            _pool = pool
            _checkpointer, _kind = cp, "postgres"
            logger.info("langgraph checkpointer: PostgresSaver")
            return _checkpointer, _kind
        except Exception as exc:
            if mode == "postgres":
                logger.exception(
                    "Postgres checkpointer required but failed — falling back to memory: %s",
                    exc,
                )
            else:
                logger.warning(
                    "Postgres checkpointer unavailable (%s) — using MemorySaver",
                    exc,
                )

    _checkpointer, _kind = MemorySaver(), "memory"
    logger.info("langgraph checkpointer: MemorySaver")
    return _checkpointer, _kind


def _build_postgres(url: str):
    if not url:
        raise RuntimeError("DATABASE_URL is empty")

    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool
    from langgraph.checkpoint.postgres import PostgresSaver

    # psycopg3 accepts postgresql:// ; normalize postgres:// if needed
    conninfo = url.replace("postgres://", "postgresql://", 1)

    pool = ConnectionPool(
        conninfo=conninfo,
        max_size=int(os.getenv("LANGGRAPH_PG_POOL_SIZE", "10")),
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
            "connect_timeout": int(os.getenv("LANGGRAPH_PG_CONNECT_TIMEOUT", "3")),
        },
        open=True,
    )
    saver = PostgresSaver(pool)
    saver.setup()
    return saver, pool


def checkpointer_kind() -> CheckpointKind:
    _, kind = get_checkpointer()
    return kind


def reset_checkpointer_cache() -> None:
    """Test helper — clear cached checkpointer."""
    global _pool, _checkpointer, _kind
    if _pool is not None:
        try:
            _pool.close()
        except Exception:
            pass
    _pool = None
    _checkpointer = None
    _kind = None
