# src/api_server.py
#!/usr/bin/env python3
"""
FastAPI service exposing:

• POST /api/local/ask   – runs the local Text2CypherAgent
• POST /api/remote/ask  – proxies question to the OpenAI Assistant
"""

import time
import asyncio
from functools import partial
from typing import Optional, Dict

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

from src.text2cypher_agent import Text2CypherAgent
from src.utils import get_env_variable
from src.schema_loader import get_schema

load_dotenv()
OPENAI_ASSISTANT_ID = get_env_variable("OPENAI_ASSISTANT_ID")
client = OpenAI()

# persistent thread for the remote assistant per session
_REMOTE_THREADS: Dict[str, str] = {}

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

# store agents by session id for multi-user support
_AGENT_STORE: Dict[str, Text2CypherAgent] = {}

def get_agent(session_id: Optional[str]) -> Text2CypherAgent:
    """Return agent for ``session_id``, creating one if needed."""
    if not session_id:
        return cypher_agent
    agent = _AGENT_STORE.get(session_id)
    if agent is None:
        agent = Text2CypherAgent()
        _AGENT_STORE[session_id] = agent
    return agent

# ── request model ────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class SessionRequest(BaseModel):
    session_id: Optional[str] = None

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
    agent = get_agent(req.session_id)
    try:
        cypher = agent.respond(q)
        return {"answer": cypher}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/remote/history", tags=["remote-agent"])
async def remote_history(session_id: Optional[str] = None):
    """Return conversation history for the remote assistant."""
    thread_id = _REMOTE_THREADS.get(session_id or "default")
    if thread_id is None:
        return {"history": []}

    msgs = client.beta.threads.messages.list(thread_id=thread_id)
    history = []
    for m in reversed(msgs.data):  # chronological order
        content = m.content[0].text.value.strip()
        history.append({"role": m.role, "content": content})
    return {"history": history}


@app.post("/api/remote/clear", tags=["remote-agent"])
async def clear_remote_history(req: SessionRequest):
    """Reset the remote assistant conversation."""
    thread_key = req.session_id or "default"
    _REMOTE_THREADS.pop(thread_key, None)
    return {"status": "cleared"}

@app.get("/api/local/history", tags=["local-agent"])
async def local_history(session_id: Optional[str] = None):
    """Return conversation history for the local agent."""
    agent = get_agent(session_id)
    return {"history": agent.get_history()}

@app.post("/api/local/clear", tags=["local-agent"])
async def clear_local_history(req: SessionRequest):
    """Clear the local agent chat history."""
    agent = get_agent(req.session_id)
    agent.clear_history()
    return {"status": "cleared"}

# --------------------------------------------------------------------
# REMOTE assistant endpoint
# --------------------------------------------------------------------
@app.post("/api/remote/ask", tags=["remote-agent"])
async def ask_remote_agent(req: QueryRequest):
    """Send a question to the remote OpenAI Assistant (stateful)."""
    q = req.query.strip()
    if not q:
        return {"error": "Query cannot be empty."}
    thread_key = req.session_id or "default"

    try:
        loop = asyncio.get_running_loop()
        # initialise thread on first use
        thread_id = _REMOTE_THREADS.get(thread_key)
        if thread_id is None:
            thread = await loop.run_in_executor(None, client.beta.threads.create)
            thread_id = thread.id
            _REMOTE_THREADS[thread_key] = thread_id

        await loop.run_in_executor(
            None,
            partial(
                client.beta.threads.messages.create,
                thread_id=thread_id,
                role="user",
                content=q,
            ),
        )

        run = await loop.run_in_executor(
            None,
            partial(
                client.beta.threads.runs.create,
                thread_id=thread_id,
                assistant_id=OPENAI_ASSISTANT_ID,
            ),
        )

        while run.status in ("queued", "in_progress"):
            await asyncio.sleep(1)
            run = await loop.run_in_executor(
                None,
                partial(
                    client.beta.threads.runs.retrieve,
                    thread_id=thread_id,
                    run_id=run.id,
                ),
            )

        msgs = await loop.run_in_executor(
            None,
            partial(client.beta.threads.messages.list, thread_id=thread_id),
        )
        # OpenAI returns most-recent first → last assistant reply is msgs.data[0]
        for m in msgs.data:
            if m.role == "assistant":
                return {"answer": m.content[0].text.value.strip()}

        return {"answer": "No response from assistant."}

    except Exception as e:
        return {"error": str(e)}
