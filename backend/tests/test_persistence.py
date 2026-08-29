"""
Tests for checkpointer + investigation store backend selection.
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

from app.services.checkpointer import get_checkpointer, reset_checkpointer_cache
from app.services.investigation_store import (
    InvestigationRunStore,
    PostgresInvestigationRunStore,
    _build_store,
    reset_investigation_store_for_tests,
)


def test_checkpointer_forced_memory(monkeypatch):
    reset_checkpointer_cache()
    monkeypatch.setenv("LANGGRAPH_CHECKPOINT", "memory")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/x")
    cp, kind = get_checkpointer()
    assert kind == "memory"
    assert isinstance(cp, MemorySaver)
    reset_checkpointer_cache()


def test_checkpointer_auto_falls_back_when_postgres_build_fails(monkeypatch):
    reset_checkpointer_cache()
    monkeypatch.setenv("LANGGRAPH_CHECKPOINT", "auto")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/x")

    def _boom(_url: str):
        raise RuntimeError("simulated postgres failure")

    monkeypatch.setattr("app.services.checkpointer._build_postgres", _boom)
    cp, kind = get_checkpointer()
    assert kind == "memory"
    assert isinstance(cp, MemorySaver)
    reset_checkpointer_cache()


def test_store_forced_memory(monkeypatch):
    monkeypatch.setenv("INVESTIGATION_STORE", "memory")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/x")
    store = _build_store()
    assert isinstance(store, InvestigationRunStore)
    assert store.backend == "memory"


def test_store_auto_falls_back_when_postgres_ctor_fails(monkeypatch):
    monkeypatch.setenv("INVESTIGATION_STORE", "auto")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/x")

    class Boom:
        def __init__(self, *_a, **_k):
            raise RuntimeError("simulated store failure")

    monkeypatch.setattr(
        "app.services.investigation_store.PostgresInvestigationRunStore",
        Boom,
    )
    store = _build_store()
    assert isinstance(store, InvestigationRunStore)
    assert store.backend == "memory"


def test_reset_investigation_store_for_tests():
    custom = InvestigationRunStore(max_runs=5)
    out = reset_investigation_store_for_tests(custom)
    assert out is custom
    custom.create("t1", question="q", mode="explore", depth="quick")
    assert custom.get("t1") is not None
    reset_investigation_store_for_tests()


def test_postgres_store_class_exists():
    assert callable(PostgresInvestigationRunStore)
