#!/usr/bin/env python3
import json
import os
import sys
import time
from threading import RLock
from typing import Dict, Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import AIMessage, HumanMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.utils import get_env_variable
from src.schema_loader import get_schema, get_schema_hints


load_dotenv()

# Histories are keyed by browser session id and shared across providers.
_SESSION_HISTORIES: Dict[str, ChatMessageHistory] = {}
_SESSION_LAST_USED: Dict[str, float] = {}
_HISTORY_LOCK = RLock()
MAX_HISTORY_MESSAGES = max(2, int(os.getenv("MAX_HISTORY_MESSAGES", "40")))
MAX_HISTORY_SESSIONS = max(1, int(os.getenv("MAX_HISTORY_SESSIONS", "500")))

SYSTEM_RULES = (
    "You are a Cypher-generating assistant. Follow these rules:\n"
    "1. Use *only* the node labels, relationship types and property names that appear in the JSON schema.\n"
    "2. If the user is revising a previous Cypher draft, update that draft; otherwise, generate a fresh query.\n"
    "3. Respond with **Cypher only** – no commentary or explanation.\n"
    "4. Return nodes and relationships only (omit scalar property values in RETURN).\n"
    "5. When the user mentions a label/relationship/property absent from the schema, first map it to the closest existing element (exact synonym, substring, or highest-similarity fuzzy match). Ask for clarification only if multiple matches are equally plausible, offering up to three suggestions.\n"
)

def make_llm(provider: str = "openai"):
    """Return a Chat instance for the specified provider."""
    if provider == "openai":
        return ChatOpenAI(
            base_url=get_env_variable(
                "OPENAI_API_BASE_URL",
                default="https://api.openai.com/v1",
            ),
            api_key=get_env_variable("OPENAI_API_KEY"),
            model=get_env_variable("OPENAI_API_MODEL")
        )
    elif provider == "google":
        return ChatGoogleGenerativeAI(
            model=get_env_variable("GOOGLE_MODEL"),
            google_api_key=get_env_variable("GOOGLE_API_KEY"),
            temperature=0
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")

class Text2CypherAgent:
    """Single‑LLM agent that remembers conversation context + schema."""

    def __init__(self, provider: str = "openai"):
        self.provider = provider
        self.schema_json = get_schema()
        self.schema_str = json.dumps(self.schema_json, indent=2)
        self.hints = get_schema_hints()
        
        # Build system prompt with schema and optional hints
        whole_schema = self.schema_str.replace('{', '{{').replace('}', '}}')
        system_prompt = SYSTEM_RULES + "\n### Schema\n" + whole_schema
        
        if self.hints:
            hints_str = json.dumps(self.hints, indent=2).replace('{', '{{').replace('}', '}}')
            system_prompt += "\n\n### Schema Hints\n" + hints_str

        self.llm = make_llm(provider)

        # build prompt template with history placeholder
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{user_input}")
        ])

        chain_core = self.prompt | self.llm

        def get_history(session_id: str):
            return self._get_or_create_history(session_id)

        self.chain = RunnableWithMessageHistory(
            chain_core,
            get_history,
            input_messages_key="user_input",
            history_messages_key="history",
        )

    @staticmethod
    def _touch_session_locked(session_id: str) -> None:
        """Update session recency and evict old sessions. Caller must hold _HISTORY_LOCK."""
        _SESSION_LAST_USED[session_id] = time.time()
        while len(_SESSION_HISTORIES) > MAX_HISTORY_SESSIONS:
            if not _SESSION_LAST_USED:
                stale_session = next(
                    (sid for sid in _SESSION_HISTORIES if sid != session_id),
                    None,
                )
                if stale_session is None:
                    break
                _SESSION_HISTORIES.pop(stale_session, None)
                continue
            candidate_sessions = [
                sid for sid in _SESSION_LAST_USED if sid != session_id
            ]
            if not candidate_sessions:
                break
            oldest_session = min(
                candidate_sessions,
                key=lambda sid: _SESSION_LAST_USED.get(sid, 0),
            )
            _SESSION_HISTORIES.pop(oldest_session, None)
            _SESSION_LAST_USED.pop(oldest_session, None)

    @staticmethod
    def _get_or_create_history(session_id: str) -> ChatMessageHistory:
        with _HISTORY_LOCK:
            history = _SESSION_HISTORIES.get(session_id)
            if history is None:
                history = ChatMessageHistory()
                _SESSION_HISTORIES[session_id] = history
            Text2CypherAgent._touch_session_locked(session_id)
            return history

    @staticmethod
    def _trim_history(session_id: str) -> None:
        if MAX_HISTORY_MESSAGES <= 0:
            return
        with _HISTORY_LOCK:
            history = _SESSION_HISTORIES.get(session_id)
            if history is None:
                return
            Text2CypherAgent._touch_session_locked(session_id)
            excess = len(history.messages) - MAX_HISTORY_MESSAGES
            if excess > 0:
                del history.messages[:excess]

    @staticmethod
    def _history_to_payload(history_messages: list) -> list[dict[str, Optional[str]]]:
        payload = []
        for msg in history_messages:
            role = "assistant" if getattr(msg, "type", "") == "ai" else "user"
            item = {"role": role, "content": msg.content}
            if role == "assistant":
                item["provider"] = getattr(msg, "additional_kwargs", {}).get("provider")
            payload.append(item)
        return payload

    @staticmethod
    def append_external_exchange(
        session_id: str,
        user_text: str,
        assistant_text: str,
        provider: str = "assistant",
    ) -> None:
        """Append non-LangChain exchanges (OpenAI Assistant endpoint) to history."""
        history = Text2CypherAgent._get_or_create_history(session_id)
        with _HISTORY_LOCK:
            history.messages.append(HumanMessage(content=user_text))
            history.messages.append(
                AIMessage(content=assistant_text, additional_kwargs={"provider": provider})
            )
        Text2CypherAgent._trim_history(session_id)

    @staticmethod
    def get_session_history(session_id: str) -> list[dict[str, Optional[str]]]:
        """Return history payload for one session without requiring an agent instance."""
        with _HISTORY_LOCK:
            history = _SESSION_HISTORIES.get(session_id)
            history_messages = list(history.messages) if history else []
            if history is not None:
                Text2CypherAgent._touch_session_locked(session_id)
        return Text2CypherAgent._history_to_payload(history_messages)

    @staticmethod
    def clear_session_history(session_id: Optional[str] = None) -> None:
        """Clear one session or all sessions without requiring an agent instance."""
        with _HISTORY_LOCK:
            if session_id is None:
                _SESSION_HISTORIES.clear()
                _SESSION_LAST_USED.clear()
            else:
                _SESSION_HISTORIES.pop(session_id, None)
                _SESSION_LAST_USED.pop(session_id, None)

    def respond(self, user_text: str, session_id: str) -> str:
        result = self.chain.invoke(
            {"user_input": user_text},
            config={"configurable": {"session_id": session_id}}
        )
        with _HISTORY_LOCK:
            history = _SESSION_HISTORIES.get(session_id)
            if history:
                for msg in reversed(history.messages):
                    if getattr(msg, "type", "") != "ai":
                        continue
                    kwargs = dict(getattr(msg, "additional_kwargs", {}) or {})
                    if kwargs.get("provider"):
                        continue
                    kwargs["provider"] = self.provider
                    msg.additional_kwargs = kwargs
                    break
        self._trim_history(session_id)
        return result.content.strip().strip("` ")

    def add_external_exchange(
        self,
        session_id: str,
        user_text: str,
        assistant_text: str,
        provider: str = "assistant",
    ) -> None:
        self.append_external_exchange(session_id, user_text, assistant_text, provider)

    def get_history(self, session_id: str) -> list[dict[str, Optional[str]]]:
        """Return chat history as list of {role, content, provider?} dicts."""
        return self.get_session_history(session_id)

    def clear_history(self, session_id: Optional[str] = None) -> None:
        """Clear one session or all sessions."""
        self.clear_session_history(session_id)

if __name__ == "__main__":
    try:
        agent = Text2CypherAgent()
    except EnvironmentError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        while True:
            txt = input("You> ").strip()
            if not txt:
                continue
            print(agent.respond(txt, session_id="cli") + "\n")
    except (KeyboardInterrupt, EOFError):
        print()
