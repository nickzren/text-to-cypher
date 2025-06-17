# src/api_server.py
#!/usr/bin/env python3
"""
FastAPI service exposing:

- POST /api/ask   – runs Text2CypherAgent with selected provider
- POST /api/assistant/ask  – proxies question to the OpenAI Assistant
"""

import os
import time
import asyncio
from pathlib import Path
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

# ── FastAPI app ───────────────────────────────────────────────────
app = FastAPI()

# ── Serve static files in production ─────────────────────────────────
# This MUST come before CORS middleware
if os.getenv("NODE_ENV") == "production":
    from fastapi.staticfiles import StaticFiles
    ui_dist = Path(__file__).parent.parent / "ui" / "dist"
    if ui_dist.exists():
        # API routes will take precedence over static files
        app.mount("/", StaticFiles(directory=str(ui_dist), html=True), name="static")

# ── CORS middleware (after static files) ─────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENAI_ASSISTANT_ID = get_env_variable("OPENAI_ASSISTANT_ID")
client = OpenAI()

# persistent thread for the assistant per session
_ASSISTANT_THREADS: Dict[str, str] = {}

# Create single instances of each provider agent that share history
_AGENT_INSTANCES = {
    "openai": None,
    "google": None
}

# Store the last used provider for each message
_MESSAGE_PROVIDERS = []

def get_or_create_agent(provider: str = "openai") -> Text2CypherAgent:
    """Get or create a singleton agent for the provider."""
    if _AGENT_INSTANCES[provider] is None:
        _AGENT_INSTANCES[provider] = Text2CypherAgent(provider=provider)
    return _AGENT_INSTANCES[provider]

# ── request models ────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str
    session_id: str  # Used for assistant threads only
    provider: Optional[str] = "openai"  # "openai" or "google"


class SessionRequest(BaseModel):
    session_id: str

# --------------------------------------------------------------------
# Schema endpoint
# --------------------------------------------------------------------
@app.get("/api/schema", tags=["schema"])
async def fetch_schema():
    """Return the cached Neo4j schema JSON."""
    return get_schema()

# --------------------------------------------------------------------
# LLM agent endpoint
# --------------------------------------------------------------------
@app.post("/api/ask", tags=["llm-agent"])
async def ask_llm_agent(req: QueryRequest):
    q = req.query.strip()
    if not q:
        return {"error": "Query cannot be empty."}
    
    provider = req.provider or "openai"
    if provider not in ["openai", "google"]:
        return {"error": f"Invalid provider: {provider}"}
    
    agent = get_or_create_agent(provider)
    try:
        # Track providers for messages
        _MESSAGE_PROVIDERS.append("user")
        _MESSAGE_PROVIDERS.append(provider)
        
        cypher = agent.respond(q)
        return {"answer": cypher}
    except Exception as e:
        print(f"Error in ask_llm_agent: {e}")
        return {"error": str(e)}


@app.get("/api/history", tags=["shared"])
async def get_shared_history(session_id: str):
    """Return shared conversation history with provider info."""
    # Use openai agent to get the shared history
    agent = get_or_create_agent("openai")
    history = agent.get_history()
    
    # Add provider information to messages
    for i, msg in enumerate(history):
        if i < len(_MESSAGE_PROVIDERS):
            if msg['role'] == 'assistant':
                msg['provider'] = _MESSAGE_PROVIDERS[i] if _MESSAGE_PROVIDERS[i] != 'user' else None
    
    return {"history": history}


@app.post("/api/clear", tags=["shared"])
async def clear_shared_history(req: SessionRequest):
    """Clear the shared chat history for all providers."""
    global _MESSAGE_PROVIDERS
    _MESSAGE_PROVIDERS = []
    
    # Clear history for all agents
    for provider in ["openai", "google"]:
        agent = get_or_create_agent(provider)
        agent.clear_history()
    # Also clear the assistant thread if it exists
    _ASSISTANT_THREADS.pop(req.session_id, None)
    return {"status": "cleared"}

# --------------------------------------------------------------------
# OpenAI Assistant endpoint
# --------------------------------------------------------------------
@app.post("/api/assistant/ask", tags=["assistant"])
async def ask_assistant(req: QueryRequest):
    """Send a question to the OpenAI Assistant (stateful)."""
    q = req.query.strip()
    if not q:
        return {"error": "Query cannot be empty."}
    
    try:
        # Track providers for messages
        _MESSAGE_PROVIDERS.append("user")
        _MESSAGE_PROVIDERS.append("assistant")
        
        loop = asyncio.get_running_loop()
        # initialise thread on first use
        thread_id = _ASSISTANT_THREADS.get(req.session_id)
        if thread_id is None:
            thread = await loop.run_in_executor(None, client.beta.threads.create)
            thread_id = thread.id
            _ASSISTANT_THREADS[req.session_id] = thread_id

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
        
        # Get the assistant's response
        for m in msgs.data:
            if m.role == "assistant":
                answer = m.content[0].text.value.strip()
                return {"answer": answer}

        return {"answer": "No response from assistant."}

    except Exception as e:
        return {"error": str(e)}