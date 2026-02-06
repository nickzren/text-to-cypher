# src/api_server.py
#!/usr/bin/env python3
"""
FastAPI service exposing:

- POST /api/ask   – runs Text2CypherAgent with selected provider
- POST /api/assistant/ask  – proxies question to the OpenAI Assistant
"""

import asyncio
import logging
import os
import re
import time
from functools import partial
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, field_validator

from src.schema_loader import get_schema
from src.text2cypher_agent import Text2CypherAgent
from src.utils import get_env_variable

logger = logging.getLogger(__name__)

load_dotenv()

# ── FastAPI app ───────────────────────────────────────────────────
app = FastAPI()


def _parse_bool(value: str, default: bool = False) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


# ── CORS middleware ─────────────────────────────────────────────────
cors_origins_raw = get_env_variable(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://localhost:8000",
)
cors_origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]
if not cors_origins:
    cors_origins = ["http://localhost:5173"]
cors_methods_raw = get_env_variable(
    "CORS_ALLOWED_METHODS",
    default="GET,POST,OPTIONS",
)
cors_methods = [method.strip().upper() for method in cors_methods_raw.split(",") if method.strip()]
if not cors_methods:
    cors_methods = ["GET", "POST", "OPTIONS"]
cors_headers_raw = get_env_variable(
    "CORS_ALLOWED_HEADERS",
    default="Content-Type,Authorization,Accept",
)
cors_headers = [header.strip() for header in cors_headers_raw.split(",") if header.strip()]
if not cors_headers:
    cors_headers = ["Content-Type", "Authorization", "Accept"]
cors_allow_credentials = _parse_bool(
    get_env_variable("CORS_ALLOW_CREDENTIALS", default="false"),
    default=False,
)
if cors_allow_credentials and "*" in cors_origins:
    raise RuntimeError(
        "CORS_ALLOWED_ORIGINS cannot contain '*' when CORS_ALLOW_CREDENTIALS is true."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=cors_methods,
    allow_headers=cors_headers,
)

# ── globals guarded by async locks ──────────────────────────────────
_openai_client: Optional[OpenAI] = None
_OPENAI_CLIENT_LOCK = asyncio.Lock()

_ASSISTANT_THREADS: Dict[str, str] = {}
_ASSISTANT_LAST_USED: Dict[str, float] = {}
_ASSISTANT_LOCK = asyncio.Lock()

_SESSION_RUN_LOCKS: Dict[str, asyncio.Lock] = {}
_SESSION_RUN_LAST_USED: Dict[str, float] = {}
_SESSION_RUN_LOCKS_GUARD = asyncio.Lock()

_AGENT_INSTANCES: Dict[str, Optional[Text2CypherAgent]] = {
    "openai": None,
    "google": None,
}
_AGENT_LOCK = asyncio.Lock()

_VALID_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
ASSISTANT_POLL_SECONDS = max(0.2, float(os.getenv("ASSISTANT_POLL_SECONDS", "1.0")))
ASSISTANT_TIMEOUT_SECONDS = max(5.0, float(os.getenv("ASSISTANT_TIMEOUT_SECONDS", "120")))
ASSISTANT_MAX_SESSIONS = max(1, int(os.getenv("ASSISTANT_MAX_SESSIONS", "200")))
MAX_SESSION_RUN_LOCKS = max(1, int(os.getenv("MAX_SESSION_RUN_LOCKS", "1000")))
MAX_QUERY_LENGTH = max(1, int(os.getenv("MAX_QUERY_LENGTH", "10000")))


def _validate_session_id(v: str) -> str:
    session_id = v.strip()
    if not session_id:
        raise ValueError("session_id cannot be empty")
    if not _VALID_SESSION_ID.fullmatch(session_id):
        raise ValueError(
            "session_id must be 1-128 characters using letters, numbers, '_' or '-'"
        )
    return session_id


def _evict_oldest_assistant_threads_locked() -> None:
    """Evict oldest assistant thread entries. Caller must hold _ASSISTANT_LOCK."""
    while len(_ASSISTANT_THREADS) > ASSISTANT_MAX_SESSIONS:
        if not _ASSISTANT_LAST_USED:
            stale_session = next(iter(_ASSISTANT_THREADS), None)
            if stale_session is None:
                break
            _ASSISTANT_THREADS.pop(stale_session, None)
            continue
        oldest_session = min(
            _ASSISTANT_LAST_USED,
            key=lambda session: _ASSISTANT_LAST_USED.get(session, 0),
        )
        _ASSISTANT_THREADS.pop(oldest_session, None)
        _ASSISTANT_LAST_USED.pop(oldest_session, None)


def _evict_session_run_locks_locked(exclude_session_id: Optional[str] = None) -> None:
    """Best-effort eviction of idle run locks. Caller must hold _SESSION_RUN_LOCKS_GUARD."""
    while len(_SESSION_RUN_LOCKS) > MAX_SESSION_RUN_LOCKS:
        if not _SESSION_RUN_LAST_USED:
            break
        evicted = False
        for session_id in sorted(
            _SESSION_RUN_LAST_USED,
            key=lambda sid: _SESSION_RUN_LAST_USED.get(sid, 0),
        ):
            if exclude_session_id is not None and session_id == exclude_session_id:
                continue
            lock = _SESSION_RUN_LOCKS.get(session_id)
            if lock is None:
                _SESSION_RUN_LAST_USED.pop(session_id, None)
                continue
            if lock.locked():
                continue
            _SESSION_RUN_LOCKS.pop(session_id, None)
            _SESSION_RUN_LAST_USED.pop(session_id, None)
            evicted = True
            break
        if not evicted:
            break


async def get_session_run_lock(session_id: str) -> asyncio.Lock:
    async with _SESSION_RUN_LOCKS_GUARD:
        lock = _SESSION_RUN_LOCKS.get(session_id)
        if lock is None:
            _evict_session_run_locks_locked(exclude_session_id=session_id)
            lock = asyncio.Lock()
            _SESSION_RUN_LOCKS[session_id] = lock
        _SESSION_RUN_LAST_USED[session_id] = time.time()
        _evict_session_run_locks_locked(exclude_session_id=session_id)
        return lock


async def get_or_create_agent(provider: str = "openai") -> Text2CypherAgent:
    """Get or create a singleton agent for the provider."""
    if provider not in _AGENT_INSTANCES:
        raise ValueError(f"Invalid provider: {provider}")

    existing = _AGENT_INSTANCES.get(provider)
    if existing is not None:
        return existing

    async with _AGENT_LOCK:
        existing = _AGENT_INSTANCES.get(provider)
        if existing is None:
            existing = Text2CypherAgent(provider=provider)
            _AGENT_INSTANCES[provider] = existing
    return existing


async def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is not None:
        return _openai_client

    async with _OPENAI_CLIENT_LOCK:
        if _openai_client is None:
            _openai_client = OpenAI(
                api_key=get_env_variable("OPENAI_API_KEY"),
                base_url=get_env_variable(
                    "OPENAI_API_BASE_URL", default="https://api.openai.com/v1"
                ),
            )
    return _openai_client


async def get_or_create_assistant_thread(session_id: str, client: OpenAI) -> str:
    loop = asyncio.get_running_loop()
    async with _ASSISTANT_LOCK:
        thread_id = _ASSISTANT_THREADS.get(session_id)
        if thread_id is None:
            thread = await loop.run_in_executor(None, client.beta.threads.create)
            thread_id = thread.id
            _ASSISTANT_THREADS[session_id] = thread_id

        _ASSISTANT_LAST_USED[session_id] = time.time()
        _evict_oldest_assistant_threads_locked()
        return thread_id


async def delete_assistant_thread(session_id: str) -> None:
    async with _ASSISTANT_LOCK:
        _ASSISTANT_THREADS.pop(session_id, None)
        _ASSISTANT_LAST_USED.pop(session_id, None)


# ── request models ────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str
    session_id: str
    provider: Optional[str] = "openai"  # "openai" or "google"

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query cannot be empty")
        if len(v) > MAX_QUERY_LENGTH:
            raise ValueError(f"Query cannot exceed {MAX_QUERY_LENGTH} characters")
        return v.strip()

    @field_validator("session_id")
    @classmethod
    def session_id_is_valid(cls, v: str) -> str:
        return _validate_session_id(v)


class SessionRequest(BaseModel):
    session_id: str

    @field_validator("session_id")
    @classmethod
    def session_id_is_valid(cls, v: str) -> str:
        return _validate_session_id(v)


# --------------------------------------------------------------------
# Health check endpoints
# --------------------------------------------------------------------
@app.get("/health", tags=["ops"])
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy"}


@app.get("/ready", tags=["ops"])
async def readiness_check():
    """Readiness check - verifies schema is loaded."""
    try:
        schema = get_schema()
        return {
            "ready": True,
            "node_types": len(schema.get("NodeTypes", {})),
            "relationship_types": len(schema.get("RelationshipTypes", {})),
        }
    except Exception:
        logger.exception("Readiness check failed")
        raise HTTPException(status_code=503, detail="Not ready")


# --------------------------------------------------------------------
# Schema endpoint
# --------------------------------------------------------------------
@app.get("/api/schema", tags=["schema"])
async def fetch_schema():
    """Return the cached Neo4j schema JSON."""
    try:
        return get_schema()
    except Exception:
        logger.exception("Schema fetch failed")
        raise HTTPException(status_code=500, detail="Schema unavailable")


# --------------------------------------------------------------------
# LLM agent endpoint
# --------------------------------------------------------------------
@app.post("/api/ask", tags=["llm-agent"])
async def ask_llm_agent(req: QueryRequest):
    provider = req.provider or "openai"
    if provider not in ["openai", "google"]:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

    try:
        session_lock = await get_session_run_lock(req.session_id)
        async with session_lock:
            agent = await get_or_create_agent(provider)
            loop = asyncio.get_running_loop()
            cypher = await loop.run_in_executor(
                None,
                partial(agent.respond, req.query, req.session_id),
            )
        return {"answer": cypher}
    except HTTPException:
        raise
    except Exception:
        logger.exception("LLM agent request failed")
        raise HTTPException(status_code=500, detail="Failed to generate Cypher query.")


@app.get("/api/history", tags=["shared"])
async def get_shared_history(session_id: str):
    """Return conversation history with provider info for a session."""
    try:
        session_id = _validate_session_id(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"history": Text2CypherAgent.get_session_history(session_id)}


@app.post("/api/clear", tags=["shared"])
async def clear_shared_history(req: SessionRequest):
    """Clear chat history and assistant thread for one session."""
    session_lock = await get_session_run_lock(req.session_id)
    async with session_lock:
        Text2CypherAgent.clear_session_history(req.session_id)
        await delete_assistant_thread(req.session_id)
    async with _SESSION_RUN_LOCKS_GUARD:
        _SESSION_RUN_LAST_USED[req.session_id] = time.time()
        _evict_session_run_locks_locked(exclude_session_id=req.session_id)
    return {"status": "cleared"}


# --------------------------------------------------------------------
# OpenAI Assistant endpoint
# --------------------------------------------------------------------
@app.post("/api/assistant/ask", tags=["assistant"])
async def ask_assistant(req: QueryRequest):
    """Send a question to the OpenAI Assistant (stateful)."""
    try:
        session_lock = await get_session_run_lock(req.session_id)
        async with session_lock:
            assistant_id = get_env_variable("OPENAI_ASSISTANT_ID")
            client = await get_openai_client()

            loop = asyncio.get_running_loop()
            thread_id = await get_or_create_assistant_thread(req.session_id, client)

            await loop.run_in_executor(
                None,
                partial(
                    client.beta.threads.messages.create,
                    thread_id=thread_id,
                    role="user",
                    content=req.query,
                ),
            )

            run = await loop.run_in_executor(
                None,
                partial(
                    client.beta.threads.runs.create,
                    thread_id=thread_id,
                    assistant_id=assistant_id,
                ),
            )

            deadline = time.monotonic() + ASSISTANT_TIMEOUT_SECONDS
            while run.status in ("queued", "in_progress"):
                if time.monotonic() >= deadline:
                    raise HTTPException(status_code=504, detail="Assistant request timed out.")

                await asyncio.sleep(ASSISTANT_POLL_SECONDS)
                run = await loop.run_in_executor(
                    None,
                    partial(
                        client.beta.threads.runs.retrieve,
                        thread_id=thread_id,
                        run_id=run.id,
                    ),
                )

            if run.status != "completed":
                logger.error("Assistant run did not complete", extra={"status": run.status})
                raise HTTPException(status_code=502, detail="Assistant run failed.")

            msgs = await loop.run_in_executor(
                None,
                partial(client.beta.threads.messages.list, thread_id=thread_id),
            )

            answer = "No response from assistant."
            for msg in msgs.data:
                if msg.role != "assistant":
                    continue
                run_id = getattr(msg, "run_id", None)
                if run_id and run_id != run.id:
                    continue
                if msg.content:
                    answer = msg.content[0].text.value.strip()
                    break

            Text2CypherAgent.append_external_exchange(
                req.session_id,
                req.query,
                answer,
                provider="assistant",
            )
        return {"answer": answer}

    except HTTPException:
        raise
    except Exception:
        logger.exception("Assistant request failed")
        raise HTTPException(status_code=500, detail="Assistant request failed.")


# ── Serve static files in production (MUST BE LAST!) ───────────────
# This must come AFTER all API routes are defined
if os.getenv("NODE_ENV") == "production":
    from fastapi.staticfiles import StaticFiles

    ui_dist = Path(__file__).parent.parent / "ui" / "dist"
    if ui_dist.exists():
        # API routes will take precedence over static files
        app.mount("/", StaticFiles(directory=str(ui_dist), html=True), name="static")
