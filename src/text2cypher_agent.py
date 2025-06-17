#!/usr/bin/env python3
import json
import uuid
import sys

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.utils import get_env_variable
from src.schema_loader import get_schema, get_schema_hints


load_dotenv()

# Single shared history store for all providers
_SHARED_HISTORY = ChatMessageHistory()

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
            base_url=get_env_variable("OPENAI_API_BASE_URL"),
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
        self.session_id = "shared"  # All agents use same session for shared history

        # build prompt template with history placeholder
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{user_input}")
        ])

        chain_core = self.prompt | self.llm

        def get_history(session_id: str):
            return _SHARED_HISTORY

        self.chain = RunnableWithMessageHistory(
            chain_core,
            get_history,
            input_messages_key="user_input",
            history_messages_key="history",
        )

    def respond(self, user_text: str) -> str:
        result = self.chain.invoke(
            {"user_input": user_text},
            config={"configurable": {"session_id": self.session_id}}
        )
        return result.content.strip().strip("` ")

    def get_history(self) -> list[dict[str, str]]:
        """Return chat history as list of {role, content} dicts."""
        messages = []
        for m in _SHARED_HISTORY.messages:
            role = "assistant" if getattr(m, "type", "") == "ai" else "user"
            messages.append({"role": role, "content": m.content})
        return messages

    def clear_history(self) -> None:
        """Clear the shared history."""
        global _SHARED_HISTORY
        _SHARED_HISTORY = ChatMessageHistory()

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
            print(agent.respond(txt) + "\n")
    except (KeyboardInterrupt, EOFError):
        print()