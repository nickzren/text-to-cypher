#!/usr/bin/env python3
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate

from utils import get_env_variable
from src.schema_retriever import SchemaRetriever

load_dotenv()

DEBUG       = get_env_variable("DEBUG") == "1"
PROVIDER    = get_env_variable("LLM_PROVIDER").lower()
SCHEMA_PATH = Path(get_env_variable("NEO4J_SCHEMA_PATH", resolve_path=True))

# OpenAI
OPENAI_BASE  = get_env_variable("OPENAI_API_BASE_URL")
OPENAI_KEY   = get_env_variable("OPENAI_API_KEY")
OPENAI_MODEL = get_env_variable("OPENAI_API_MODEL")

# DeepSeek
DEEPSEEK_BASE  = get_env_variable("DEEPSEEK_API_BASE_URL")
DEEPSEEK_KEY   = get_env_variable("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = get_env_variable("DEEPSEEK_API_MODEL")

# Google Gemini
GOOGLE_KEY   = get_env_variable("GOOGLE_API_KEY")
GOOGLE_MODEL = get_env_variable("GOOGLE_MODEL")

SYSTEM_TMPL = (
    "You are a Cypher-generating assistant. "
    "Your only reference is the JSON Neo4j schema below.\n\n"
    "User question:\n{question}\n\n"
    "Schema:\n{schema}\n\n"
    "Follow these exact steps for every user query:\n\n"
    "1. Extract Entities from User Query:\n"
    "- Parse the question for domain concepts and map them to schema elements.\n"
    "- Identify candidate node types, relationship types, properties, and constraints.\n\n"
    "2. Validate Against the Schema:\n"
    "- Ensure every node label, relationship type, and property exists in the schema exactly.\n\n"
    "3. Return Clause Strategy:\n"
    "- RETURN every node and edge mentioned unless the user requests specific properties.\n\n"
    "4. Final Cypher Script Generation:\n"
    "- Respond with only the final Cypher query—no commentary or extra text.\n"
)

def make_llm():
    if PROVIDER == "deepseek":
        return ChatOpenAI(
            base_url=DEEPSEEK_BASE,
            api_key=DEEPSEEK_KEY,
            model=DEEPSEEK_MODEL,
            temperature=0.0,
        )
    if PROVIDER == "google":
        return ChatGoogleGenerativeAI(
            model=GOOGLE_MODEL,
            google_api_key=GOOGLE_KEY,
            temperature=0.0,
        )
    return ChatOpenAI(
        base_url=OPENAI_BASE,
        api_key=OPENAI_KEY,
        model=OPENAI_MODEL,
        temperature=0.0,
    )

class Text2CypherAgent:
    def __init__(self):
        self.retriever = SchemaRetriever(SCHEMA_PATH)
        self.llm = make_llm()
        self.pipeline = (
            PromptTemplate(
                input_variables=["schema", "question"],
                template=SYSTEM_TMPL,
            )
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
    except (KeyboardInterrupt, EOFError):
        print()