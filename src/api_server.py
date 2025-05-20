# src/api_server.py
#!/usr/bin/env python3
"""
FastAPI service exposing:

• POST /api/local/ask   – runs the local Text2CypherAgent
• POST /api/remote/ask  – proxies question to the OpenAI Assistant
"""

import time
import asyncio
import os
import json
from functools import partial
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from neo4j import GraphDatabase

from src.text2cypher_agent import Text2CypherAgent
from src.utils import get_env_variable
from src.schema_loader import get_schema

load_dotenv()
OPENAI_ASSISTANT_ID = get_env_variable("OPENAI_ASSISTANT_ID")
client = OpenAI()

# ── Neo4j driver for running queries ──────────────────────────────────
_DB_URI = get_env_variable("DB_URL")
_DB_NAME = get_env_variable("DB_NAME")
_DB_USER = os.getenv("DB_USER")
_DB_PASSWORD = os.getenv("DB_PASSWORD")
_neo4j_driver = GraphDatabase.driver(
    _DB_URI,
    auth=(_DB_USER, _DB_PASSWORD) if _DB_USER else None,
)

# in-memory store for query results so they appear in history
_RUN_HISTORY: List[Dict[str, Any]] = []

# persistent thread for the remote assistant
_REMOTE_THREAD_ID: Optional[str] = None

# ── FastAPI app & CORS ───────────────────────────────────────────────
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── local Text‑to‑Cypher agent (schema retriever inside) ─────────────
cypher_agent = Text2CypherAgent()

# ── request model ────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str

# --------------------------------------------------------------------
# Schema endpoint
# --------------------------------------------------------------------
@app.get("/api/schema", tags=["schema"])
async def fetch_schema():
    """Return the cached Neo4j schema JSON."""
    return get_schema()

# --------------------------------------------------------------------
# LOCAL agent endpoint
# --------------------------------------------------------------------
@app.post("/api/local/ask", tags=["local-agent"])
async def ask_local_agent(req: QueryRequest):
    q = req.query.strip()
    if not q:
        return {"error": "Query cannot be empty."}
    try:
        cypher = cypher_agent.respond(q)
        return {"answer": cypher}
    except Exception as e:
        return {"error": str(e)}


# --------------------------------------------------------------------
# Run Cypher query
# --------------------------------------------------------------------
@app.post("/api/run", tags=["run"])
async def run_query(req: QueryRequest):
    """Execute the given Cypher query against Neo4j."""
    q = req.query.strip()
    if not q:
        return {"error": "Query cannot be empty."}
    try:
        with _neo4j_driver.session(database=_DB_NAME) as session:
            records = [dict(r) for r in session.run(q)]
        _RUN_HISTORY.append({"role": "result", "content": json.dumps(records)})
        return {"records": records}
    except Exception as e:
        msg = str(e)
        _RUN_HISTORY.append({"role": "result", "content": f"Error: {msg}"})
        return {"error": msg}


@app.get("/api/remote/history", tags=["remote-agent"])
async def remote_history():
    """Return conversation history for the remote assistant."""
    if _REMOTE_THREAD_ID is None:
        return {"history": _RUN_HISTORY}

    msgs = client.beta.threads.messages.list(thread_id=_REMOTE_THREAD_ID)
    history = []
    for m in reversed(msgs.data):  # chronological order
        content = m.content[0].text.value.strip()
        history.append({"role": m.role, "content": content})
    history.extend(_RUN_HISTORY)
    return {"history": history}


@app.post("/api/remote/clear", tags=["remote-agent"])
async def clear_remote_history():
    """Reset the remote assistant conversation."""
    global _REMOTE_THREAD_ID
    _REMOTE_THREAD_ID = None
    _RUN_HISTORY.clear()
    return {"status": "cleared"}

@app.get("/api/local/history", tags=["local-agent"])
async def local_history():
    """Return conversation history for the local agent."""
    return {"history": cypher_agent.get_history() + _RUN_HISTORY}

@app.post("/api/local/clear", tags=["local-agent"])
async def clear_local_history():
    """Clear the local agent chat history."""
    cypher_agent.clear_history()
    _RUN_HISTORY.clear()
    return {"status": "cleared"}

# --------------------------------------------------------------------
# REMOTE assistant endpoint
# --------------------------------------------------------------------
@app.post("/api/remote/ask", tags=["remote-agent"])
async def ask_remote_agent(req: QueryRequest):
    """Send a question to the remote OpenAI Assistant (stateful)."""
    global _REMOTE_THREAD_ID
    q = req.query.strip()
    if not q:
        return {"error": "Query cannot be empty."}

    try:
        loop = asyncio.get_running_loop()
        # initialise thread on first use
        if _REMOTE_THREAD_ID is None:
            thread = await loop.run_in_executor(None, client.beta.threads.create)
            _REMOTE_THREAD_ID = thread.id

        await loop.run_in_executor(
            None,
            partial(
                client.beta.threads.messages.create,
                thread_id=_REMOTE_THREAD_ID,
                role="user",
                content=q,
            ),
        )

        run = await loop.run_in_executor(
            None,
            partial(
                client.beta.threads.runs.create,
                thread_id=_REMOTE_THREAD_ID,
                assistant_id=OPENAI_ASSISTANT_ID,
            ),
        )

        while run.status in ("queued", "in_progress"):
            await asyncio.sleep(1)
            run = await loop.run_in_executor(
                None,
                partial(
                    client.beta.threads.runs.retrieve,
                    thread_id=_REMOTE_THREAD_ID,
                    run_id=run.id,
                ),
            )

        msgs = await loop.run_in_executor(
            None,
            partial(client.beta.threads.messages.list, thread_id=_REMOTE_THREAD_ID),
        )
        # OpenAI returns most-recent first → last assistant reply is msgs.data[0]
        for m in msgs.data:
            if m.role == "assistant":
                return {"answer": m.content[0].text.value.strip()}

        return {"answer": "No response from assistant."}

    except Exception as e:
        return {"error": str(e)}
