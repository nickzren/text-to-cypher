#!/usr/bin/env python3
"""
schema_retriever.py
Given a natural-language question, return the minimal relevant slice
(NodeTypes + RelationshipTypes) from the Neo4j schema.
"""

from __future__ import annotations
import json, os, re, string, sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Set

import faiss, numpy as np
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

from schema_index_builder import ensure_index          # ← new import

# ── env & constants ────────────────────────────────────────────────────
load_dotenv()
SCHEMA_PATH = Path(os.environ["NEO4J_SCHEMA_PATH"]).expanduser().resolve()
INDEX_PATH  = SCHEMA_PATH.with_suffix(".faiss")
ROWS_PATH   = SCHEMA_PATH.with_suffix(".rows.npy")

EMBED_MODEL  = "text-embedding-3-small"
K_QUESTION, K_TOKEN, TOP_K = 15, 5, 50
TAU, EXACT_WT, TOKEN_WT    = 0.18, 4.0, 0.5
DEBUG_SCHEMA  = os.getenv("DEBUG_SCHEMA", "0") == "1"

# ── cheap lexer ---------------------------------------------------------
STOPWORDS = {"a","an","the","in","on","of","to","and","with",
             "for","from","into","by","at","between","among"}
def stem(w: str) -> str:
    for suf in ("ing","ed","es","s"):
        if w.endswith(suf) and len(w) > len(suf)+2:
            return w[:-len(suf)]
    return w
def tokens(text: str) -> Set[str]:
    return {stem(t.lower().strip(string.punctuation))
            for t in re.findall(r"[A-Za-z0-9_-]+", text)
            if len(t) > 2 and t.lower() not in STOPWORDS}

# ── main class ----------------------------------------------------------
class SchemaRetriever:
    def __init__(self, schema_path: Path = SCHEMA_PATH):
        ensure_index()                                   # make sure index exists
        self.schema = json.loads(schema_path.read_text())
        self.rows   = np.load(ROWS_PATH, allow_pickle=True)
        self.index  = faiss.read_index(str(INDEX_PATH))
        self.emb    = OpenAIEmbeddings(model=EMBED_MODEL)
        self.node_labels = set(self.schema["NodeTypes"])
        self.rel_types   = set(self.schema["RelationshipTypes"])

    # ------------------------------------------------------------------
    def __call__(self, question: str) -> str:
        toks   = tokens(question)
        scores = defaultdict(float)

        # full-question similarity
        qv = np.array(self.emb.embed_query(question)).astype("float32")
        qv /= np.linalg.norm(qv)+1e-8
        sims, idxs = self.index.search(qv[None,:], K_QUESTION)
        for i,s in zip(idxs[0], sims[0]):
            if s>0: scores[self.rows[i]] += s

        # token similarities + exact match
        for tok in toks:
            tv = np.array(self.emb.embed_query(tok)).astype("float32")
            tv /= np.linalg.norm(tv)+1e-8
            sims_t, idxs_t = self.index.search(tv[None,:], K_TOKEN)
            for i,s in zip(idxs_t[0], sims_t[0]):
                if s>0: scores[self.rows[i]] += TOKEN_WT*s

            for row in self.rows:                        # exact match per row
                row_toks = {stem(x.lower())
                            for x in re.split(r'[^A-Za-z0-9]+', row) if x}
                if tok in row_toks: scores[row] += EXACT_WT

        if not scores: return json.dumps(self.schema, indent=2)
        best = max(scores.values())
        cand = [r for r,s in scores.items() if s>=best*TAU][:TOP_K]

        labels, rels, props = set(), set(), set()
        for r in cand:
            if "." in r: props.add(r)
            elif r in self.rel_types: rels.add(r)
            elif r in self.node_labels: labels.add(r)

        for p in props:                                 # parent propagation
            parent = p.split(".",1)[0]
            (labels if parent in self.node_labels else rels).add(parent)

        for rel in list(rels):                          # endpoint propagation
            ep = self.schema["RelationshipTypes"][rel].get("_endpoints")
            if ep:
                labels.update(l for l in ep if l in self.node_labels)
            else:
                a,b,*_ = rel.split("_")
                if a in self.node_labels: labels.add(a)
                if b in self.node_labels: labels.add(b)

        referenced = {
            lbl for rel in rels
            for lbl in (
                self.schema["RelationshipTypes"][rel].get("_endpoints")
                or [rel.split("_")[0], rel.split("_")[-1]]
            ) if lbl in self.node_labels
        }
        labels |= referenced                           # ensure endpoints kept

        if DEBUG_SCHEMA:
            print("labels:",sorted(labels)); print("rels:",sorted(rels))

        return json.dumps({
            "NodeTypes": {l:self.schema["NodeTypes"][l] for l in sorted(labels)},
            "RelationshipTypes": {r:self.schema["RelationshipTypes"][r] for r in sorted(rels)}
        }, indent=2)

# ── CLI ---------------------------------------------------------------
def main():
    if not SCHEMA_PATH.exists():
        sys.exit("schema file not found")
    retriever = SchemaRetriever()
    try:
        while True:
            q = input("Question> ").strip()
            if q: print(retriever(q))
    except KeyboardInterrupt:
        print()

if __name__ == "__main__":
    main()