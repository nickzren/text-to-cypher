#!/usr/bin/env python3
"""
Text2CypherAgent
----------------
1. Uses SchemaRetriever to slice the Neo4j schema.
2. Passes the slice and the question to an OpenAI (or DeepSeek) chat model.
3. Returns ONLY the Cypher query.
"""

import os, sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

from src.schema_retriever import SchemaRetriever   

load_dotenv()
DEBUG = os.getenv("DEBUG", "0") == "1"

PROVIDER      = os.getenv("LLM_PROVIDER")
SCHEMA_PATH   = Path(os.environ["NEO4J_SCHEMA_PATH"])

OPENAI_BASE   = os.getenv("OPENAI_API_BASE_URL")
OPENAI_KEY    = os.environ["OPENAI_API_KEY"]
OPENAI_MODEL  = os.getenv("OPENAI_API_MODEL")

DEEPSEEK_BASE     = os.getenv("DEEPSEEK_API_BASE_URL")
DEEPSEEK_KEY      = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL    = os.getenv("DEEPSEEK_API_MODEL")

SYSTEM_TMPL = (
    "You are a Cypher‑generating assistant. "
    "Your sole reference for generating Cypher scripts is the `neo4j_schema` variable.\n\n"
    "User question:\n{question}\n\n"
    "The schema is defined below in JSON format:\n"
    "{schema}\n\n"
    "Follow these exact steps for every user query:\n\n"
    "1. Extract Entities from User Query:\n"
    "- Parse the question for domain concepts and use synonyms or contextual cues to map them to schema elements.\n"
    "- Identify candidate **node types**.\n"
    "- Identify candidate **relationship types**.\n"
    "- Identify relevant **properties**.\n"
    "- Identify **constraints or conditions** (comparisons, flags, temporal filters, shared‑entity references, etc.).\n\n"
    "2. Validate Against the Schema:\n"
    "- Ensure every node label, relationship type, and property exists in the schema **exactly** (case‑ and character‑sensitive).\n"
    "- If any required element is missing, respond exactly:\n"
    '  \"I could not generate a Cypher script; the required information is not part of the Neo4j schema.\"\n\n'
    "3. Construct the MATCH Pattern:\n"
    "- Use only schema‑validated node labels and relationship types.\n"
    "- Reuse a single variable whenever the query implies that two patterns refer to the same node.\n"
    "- Express simple equality predicates in map patterns and move all other filters to a **WHERE** clause.\n\n"
    "4. Return Clause Strategy:\n"
    "- RETURN every node and relationship mentioned, unless the user explicitly requests specific properties.\n\n"
    "5. Final Cypher Script Generation:\n"
    "- Respond with **only** the final Cypher query—no commentary or extra text.\n"
    "- Use OPTIONAL MATCH only if explicitly required by the user and supported by the schema.\n"
)

def make_llm() -> ChatOpenAI:
    if PROVIDER.lower() == "deepseek":
        return ChatOpenAI(base_url=DEEPSEEK_BASE, api_key=DEEPSEEK_KEY, model=DEEPSEEK_MODEL)
    return ChatOpenAI(base_url=OPENAI_BASE, api_key=OPENAI_KEY, model=OPENAI_MODEL)

class Text2CypherAgent:
    def __init__(self):
        self.retriever = SchemaRetriever(SCHEMA_PATH)
        self.llm       = make_llm()
        name = getattr(self.llm, "model_name", getattr(self.llm, "model", "unknown"))
        print(f"[INFO] Text2CypherAgent using LLM = {name}")
        self.pipeline  = (
            PromptTemplate(input_variables=["schema", "question"],
                           template=SYSTEM_TMPL)
            | self.llm
        )

    def generate(self, question: str) -> str:
        schema_slice = self.retriever(question)
        if DEBUG:
            print("[DEBUG] Schema slice:\n", schema_slice, file=sys.stderr)
        msg = self.pipeline.invoke({"schema": schema_slice, "question": question})
        return str(getattr(msg, "content", msg)).strip()

if __name__ == "__main__":
    agent = Text2CypherAgent()
    try:
        while True:
            q = input("Ask> ").strip()
            if q:
                print("\n" + agent.generate(q) + "\n")
    except KeyboardInterrupt:
        print()