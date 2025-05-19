#!/usr/bin/env python3
import json
import uuid

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

from utils import get_env_variable
from schema_loader import get_schema


load_dotenv()

_HISTORY_STORE: dict[str, ChatMessageHistory] = {}

SYSTEM_RULES = (
    "You are a Cypher-generating assistant. Follow these rules:\n"
    "1. Use *only* the node labels, relationship types and property names that appear in the JSON schema.\n"
    "2. If the user is revising a previous Cypher draft, update that draft; otherwise, generate a fresh query.\n"
    "3. Respond with **Cypher only** – no commentary or explanation.\n"
    "4. Return nodes and relationships only (omit scalar property values in RETURN).\n"
    "5. When the user mentions a label/relationship/property absent from the schema, first map it to the closest existing element (exact synonym, substring, or highest-similarity fuzzy match). Ask for clarification only if multiple matches are equally plausible, offering up to three suggestions.\n"
)

def make_llm():
    """Return a temperature‑0 ChatOpenAI instance (OpenAI‑only)."""
    return ChatOpenAI(
        base_url=get_env_variable("OPENAI_API_BASE_URL"),
        api_key=get_env_variable("OPENAI_API_KEY"),
        model=get_env_variable("OPENAI_API_MODEL")
    )

class Text2CypherAgent:
    """Single‑LLM agent that remembers conversation context + schema."""

    def __init__(self):
        self.schema_json = get_schema()
        self.schema_str = json.dumps(self.schema_json, indent=2)
        whole_schema = self.schema_str.replace('{', '{{').replace('}', '}}')
        self.llm        = make_llm()
        self.session_id = str(uuid.uuid4())

        # build prompt template with history placeholder
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_RULES + "\n### Schema\n" + whole_schema),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{user_input}")
        ])

        chain_core = self.prompt | self.llm

        def get_history(session_id: str):
            if session_id not in _HISTORY_STORE:
                _HISTORY_STORE[session_id] = ChatMessageHistory()
            return _HISTORY_STORE[session_id]

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

if __name__ == "__main__":
    agent = Text2CypherAgent()
    try:
        while True:
            txt = input("You> ").strip()
            if not txt:
                continue
            print(agent.respond(txt) + "\n")
    except (KeyboardInterrupt, EOFError):
        print()