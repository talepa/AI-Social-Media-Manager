"""
services/research_cache.py

Disk-backed cache for research gather + report synthesize.
Same topic/limit (and same sources for synthesize) → cache hit → skip paid APIs.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# backend/.cache/research
_DEFAULT_DIR = Path(__file__).resolve().parents[2] / ".cache" / "research"


def _enabled() -> bool:
    return os.getenv("RESEARCH_CACHE_ENABLED", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _ttl_seconds() -> int:
    raw = os.getenv("RESEARCH_CACHE_TTL_SECONDS", str(60 * 60 * 24))
    try:
        return max(60, int(raw))
    except ValueError:
        return 60 * 60 * 24


def _cache_dir() -> Path:
    override = os.getenv("RESEARCH_CACHE_DIR", "").strip()
    path = Path(override) if override else _DEFAULT_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def normalize_topic(topic: str) -> str:
    return " ".join((topic or "").lower().split())


def _digest(parts: list[str]) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def multi_cache_key(topic: str, limit: int) -> str:
    return _digest(["multi", "v4-previews", normalize_topic(topic), str(int(limit))])


def synthesize_cache_key(
    topic: str,
    *,
    use_llm: bool,
    tavily_urls: list[str],
    news_urls: list[str],
    papers_urls: list[str],
) -> str:
    urls = sorted({*(tavily_urls or []), *(news_urls or []), *(papers_urls or [])})
    return _digest(
        [
            "synthesize",
            "v1",
            normalize_topic(topic),
            "llm" if use_llm else "compile",
            ",".join(urls),
        ]
    )


def _path_for(key: str) -> Path:
    return _cache_dir() / f"{key}.json"


def get_cached(key: str, model: Type[T]) -> Optional[T]:
    if not _enabled():
        return None
    path = _path_for(key)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        saved_at = float(payload.get("saved_at") or 0)
        if time.time() - saved_at > _ttl_seconds():
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            return None
        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        return model.model_validate(data)
    except Exception:
        logger.exception("Failed reading cache key=%s", key[:12])
        return None


def set_cached(key: str, value: BaseModel) -> None:
    if not _enabled():
        return
    path = _path_for(key)
    try:
        envelope: dict[str, Any] = {
            "saved_at": time.time(),
            "key": key,
            "data": value.model_dump(mode="json"),
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
    except Exception:
        logger.exception("Failed writing cache key=%s", key[:12])
