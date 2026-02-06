#!/usr/bin/env python3
"""
schema_loader.py
Fast, memoised accessor for the Neo4j schema JSON and optional hints.

Usage
-----
from schema_loader import get_schema, get_schema_hints
schema = get_schema()       # dict, loaded once per process
hints = get_schema_hints()  # dict or None, loaded once per process
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from threading import RLock
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from src.utils import get_project_root

load_dotenv()

# ── internal cache --------------------------------------------------------
_cached_schema: Dict[str, Any] | None = None
_cached_hints: Dict[str, Any] | None = None
_hints_loaded: bool = False
_CACHE_LOCK = RLock()


def _resolve_config_path(raw_path: Optional[str]) -> Optional[Path]:
    """Resolve config path relative to project root when not absolute."""
    if not raw_path:
        return None
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = (get_project_root() / path).resolve()
    else:
        path = path.resolve()
    return path


def _get_schema_path() -> Path:
    raw_path = os.getenv("NEO4J_SCHEMA_PATH", "data/input/neo4j_schema.json")
    path = _resolve_config_path(raw_path)
    if path is None:
        raise RuntimeError("NEO4J_SCHEMA_PATH is not configured.")
    return path


def _get_hints_path() -> Optional[Path]:
    return _resolve_config_path(os.getenv("SCHEMA_HINTS_PATH"))


def get_schema() -> Dict[str, Any]:
    """Return the Neo4j schema as a JSON dict (cached)."""
    global _cached_schema
    if _cached_schema is not None:
        return _cached_schema
    with _CACHE_LOCK:
        if _cached_schema is None:
            schema_path = _get_schema_path()
            if not schema_path.exists():
                raise FileNotFoundError(f"Schema file not found: {schema_path}")
            with schema_path.open(encoding="utf-8") as f:
                _cached_schema = json.load(f)
    return _cached_schema


def get_schema_hints() -> Optional[Dict[str, Any]]:
    """Return schema hints/clarifications if available (cached)."""
    global _cached_hints, _hints_loaded
    if _hints_loaded:
        return _cached_hints
    with _CACHE_LOCK:
        if not _hints_loaded:
            hints_path = _get_hints_path()
            if hints_path and hints_path.exists():
                with hints_path.open(encoding="utf-8") as f:
                    _cached_hints = json.load(f)
            _hints_loaded = True
    return _cached_hints
