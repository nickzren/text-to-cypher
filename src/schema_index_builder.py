#!/usr/bin/env python3
"""
schema_index_builder.py
Build (or rebuild) the FAISS index + rows.npy for a Neo4j schema.
Also ensures required NLTK data files are present.
"""

from __future__ import annotations
import json, os, sys
from pathlib import Path
from typing import Dict, Iterable

import faiss
import numpy as np
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings


# ── env & paths ────────────────────────────────────────────────────────
load_dotenv()
SCHEMA_PATH = Path(os.environ["NEO4J_SCHEMA_PATH"]).expanduser().resolve()
INDEX_PATH  = SCHEMA_PATH.with_suffix(".faiss")
ROWS_PATH   = SCHEMA_PATH.with_suffix(".rows.npy")
EMBED_MODEL = "text-embedding-3-small"

# ── helpers ────────────────────────────────────────────────────────────
def iter_schema_rows(schema: Dict) -> Iterable[str]:
    labels = list(schema["NodeTypes"])
    rels   = list(schema["RelationshipTypes"])
    props  = [
        f"{parent}.{prop}"
        for parent, fields in (
            list(schema["NodeTypes"].items()) +
            list(schema["RelationshipTypes"].items())
        )
        for prop in fields
    ]
    # keep order but remove dups
    return dict.fromkeys(labels + rels + props).keys()

# ── public API ─────────────────────────────────────────────────────────
def ensure_index(schema_path: Path = SCHEMA_PATH,
                 index_path: Path = INDEX_PATH,
                 rows_path: Path = ROWS_PATH,
                 force: bool = False) -> None:
    """Build index if missing, outdated, or force=True."""
    rebuild = force or not (index_path.exists() and rows_path.exists())
    if not rebuild:
        rebuild = schema_path.stat().st_mtime > index_path.stat().st_mtime
    if not rebuild:
        return

    schema = json.loads(schema_path.read_text())
    rows   = np.array(list(iter_schema_rows(schema)))
    embed  = OpenAIEmbeddings(model=EMBED_MODEL)
    vecs   = np.vstack([embed.embed_query(r) for r in rows]).astype("float32")
    faiss.normalize_L2(vecs)
    idx = faiss.IndexFlatIP(vecs.shape[1]); idx.add(vecs)
    faiss.write_index(idx, str(index_path))
    np.save(rows_path, rows)
    print(f"[schema-index] built {index_path.name} ({len(rows)} rows)")

# ── CLI (optional) ------------------------------------------------------
if __name__ == "__main__":
    ensure_index(force=True)