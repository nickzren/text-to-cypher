#!/usr/bin/env python3
"""
schema_loader.py
Fast, memoised accessor for the Neo4j schema JSON.

Usage
-----
from schema_loader import get_schema
schema = get_schema()   # dict, loaded once per process
"""

from __future__ import annotations
import json, os
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv

load_dotenv()
_SCHEMA_PATH = Path(os.environ["NEO4J_SCHEMA_PATH"]).expanduser().resolve()

# ── internal cache --------------------------------------------------------
_cached: Dict[str, Any] | None = None

def get_schema() -> Dict[str, Any]:
    """Return the Neo4j schema as a JSON dict (cached)."""
    global _cached
    if _cached is None:
        with _SCHEMA_PATH.open() as f:
            _cached = json.load(f)
    return _cached