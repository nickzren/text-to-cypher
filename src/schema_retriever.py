from __future__ import annotations
import json, re, string
from pathlib import Path
from typing import Dict, List, Set

import faiss, numpy as np
from langchain_openai import OpenAIEmbeddings

# ── configuration ────────────────────────────────────────────────────
EMBED_MODEL   = "text-embedding-3-small"
TOP_K_EMBED   = 10              # nearest rows to pull from FAISS
TOP_N_ROWS    = 20              # rows kept after scoring

STOPWORDS = {
    "a","an","the","in","on","of","to","and","with",
    "for","from","into","by","at","between","among"
}
WEIGHT_EXACT  = 3               # weight for exact‑token hits
# --------------------------------------------------------------------

def stem(word: str) -> str:
    """Very light stemmer: strips common suffixes."""
    for suf in ("ing", "ed", "es", "s"):
        if word.endswith(suf) and len(word) > len(suf)+2:
            return word[:-len(suf)]
    return word


class SchemaRetriever:
    """Return a minimal JSON slice of the schema relevant to a question."""

    def __init__(self, schema_path: Path):
        self.schema: Dict = json.loads(schema_path.read_text())

        self.labels: List[str] = list(self.schema["NodeTypes"])
        self.rels:   List[str] = list(self.schema["RelationshipTypes"])
        self.props:  List[str] = [
            f"{parent}.{prop}"
            for parent, fields in (
                list(self.schema["NodeTypes"].items())
                + list(self.schema["RelationshipTypes"].items())
            )
            for prop in fields
        ]
        self.rows = self.labels + self.rels + self.props

        emb = OpenAIEmbeddings(model=EMBED_MODEL)
        vecs = np.vstack([emb.embed_query(r) for r in self.rows]).astype("float32")
        self.index = faiss.IndexFlatL2(vecs.shape[1])
        self.index.add(vecs)
        self.emb_model = emb

    # ─────────────────────────────────────────────────────────────────
    def __call__(self, question: str) -> str:
        exact_hits = self._token_hits(question)
        embed_hits = self._embedding_hits(question)

        scores: Dict[str, float] = {}
        for row in exact_hits:
            scores[row] = scores.get(row, 0) + WEIGHT_EXACT
        for rank, row in enumerate(embed_hits, 1):
            scores[row] = scores.get(row, 0) + 1 / rank

        top_rows = [r for r, _ in sorted(scores.items(),
                                         key=lambda kv: -kv[1])][:TOP_N_ROWS]

        labels, rels, props = set(), set(), set()
        for r in top_rows:
            if "." in r:
                props.add(r)
            elif "_" in r:
                rels.add(r)
            else:
                labels.add(r)

        # properties → parent entity
        for pr in props:
            parent = pr.split(".")[0]
            (labels if parent in self.labels else rels).add(parent)

        # relationships → endpoint labels
        for rel in rels:
            ep = self.schema["RelationshipTypes"][rel].get("_endpoints")
            if ep:                                   # use explicit mapping
                labels.update({lbl for lbl in ep if lbl in self.labels})
            else:                                    # fallback to name tokens
                parts = rel.split("_")
                if len(parts) >= 2:
                    lft, rgt = parts[0], parts[-1]
                    if lft in self.labels: labels.add(lft)
                    if rgt in self.labels: labels.add(rgt)

        # safety fallback
        if not labels and not rels:
            return json.dumps(self.schema, indent=2)

        return json.dumps(
            {
                "NodeTypes":         {l: self.schema["NodeTypes"][l] for l in labels},
                "RelationshipTypes": {r: self.schema["RelationshipTypes"][r] for r in rels},
            },
            indent=2,
        )

    # ── helpers ──────────────────────────────────────────────────────
    def _embedding_hits(self, question: str) -> List[str]:
        qv = np.array(self.emb_model.embed_query(question)).astype("float32")
        _, idx = self.index.search(qv[None, :], TOP_K_EMBED)
        return [self.rows[i] for i in idx[0]]

    def _token_hits(self, question: str) -> Set[str]:
        tokens = {
            stem(w.lower().strip(string.punctuation))
            for w in re.findall(r"\w+", question)
            if len(w) > 2 and w.lower() not in STOPWORDS
        }
        hits = set()
        for tok in tokens:
            hits |= {row for row in self.rows if re.search(fr"\b{tok}\w*\b", row, re.I)}
        return hits