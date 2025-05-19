# src/api_server.py
#!/usr/bin/env python3
"""
FastAPI service exposing:

• POST /api/local/ask   – runs the local Text2CypherAgent
• POST /api/remote/ask  – proxies question to the OpenAI Assistant
"""

import time
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

from src.text2cypher_agent import Text2CypherAgent
from src.utils import get_env_variable

load_dotenv()
OPENAI_ASSISTANT_ID = get_env_variable("OPENAI_ASSISTANT_ID")
client = OpenAI()

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

@app.get("/api/local/history", tags=["local-agent"])
async def local_history():
    """Return conversation history for the local agent."""
    return {"history": cypher_agent.get_history()}

@app.post("/api/local/clear", tags=["local-agent"])
async def clear_local_history():
    """Clear the local agent chat history."""
    cypher_agent.clear_history()
    return {"status": "cleared"}

# --------------------------------------------------------------------
# REMOTE assistant endpoint
# --------------------------------------------------------------------
@app.post("/api/remote/ask", tags=["remote-agent"])
async def ask_remote_agent(req: QueryRequest):
    q = req.query.strip()
    if not q:
        return {"error": "Query cannot be empty."}

    try:
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(thread_id=thread.id, role="user", content=q)

        run = client.beta.threads.runs.create(
            thread_id=thread.id, assistant_id=OPENAI_ASSISTANT_ID
        )

        while run.status in ("queued", "in_progress"):
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        msgs = client.beta.threads.messages.list(thread_id=thread.id)
        for m in msgs.data:
            if m.role == "assistant":
                return {"answer": m.content[0].text.value.strip()}

        return {"answer": "No response from assistant."}

    except Exception as e:
        return {"error": str(e)}
