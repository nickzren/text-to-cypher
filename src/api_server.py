from fastapi import FastAPI
from pydantic import BaseModel
import json
from openai import OpenAI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from src.utils import get_env_variable
import time

load_dotenv()

LLM_PROVIDER = get_env_variable("LLM_PROVIDER", "openai")

if LLM_PROVIDER == 'openai':
    API_BASE_URL = get_env_variable("OPENAI_API_BASE_URL")
    API_KEY = get_env_variable("OPENAI_API_KEY")
    API_MODEL = get_env_variable("OPENAI_API_MODEL")
else:
    API_BASE_URL = get_env_variable("DEEPSEEK_API_BASE_URL")
    API_KEY = get_env_variable("DEEPSEEK_API_KEY")
    API_MODEL = get_env_variable("DEEPSEEK_API_MODEL")

OPENAI_ASSISTANT_ID = get_env_variable("OPENAI_ASSISTANT_ID")

client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load schema using project-aware utility
schema_path = get_env_variable("NEO4J_SCHEMA_PATH", resolve_path=True)
with open(schema_path, "r") as f:
    neo4j_schema = json.load(f)

class QueryRequest(BaseModel):
    query: str

# This endpoint uses a general LLM model (e.g., OpenAI or DeepSeek) directly via `chat.completions`
@app.post("/api/ask")
async def ask_llm(request: QueryRequest):
    user_query = request.query.strip()

    system_prompt = (
        "You are an expert Cypher query generator for a Neo4j knowledge graph.\n\n"
        "The schema is defined below in JSON format:\n"
        f"{json.dumps(neo4j_schema, indent=2)}\n\n"
        "Your task is to convert a user's natural language question into a valid Cypher query "
        "that strictly conforms to the schema. Follow these instructions step-by-step:\n\n"
        "1. Extract Entities from User Query\n"
        "- Identify node types\n"
        "- Identify relationship types\n"
        "- Identify relevant properties\n"
        "- Recognize constraints or conditions\n\n"
        "2. Validate Against the Schema\n"
        "- Check that each node label, relationship type, and property exists in the schema.\n"
        "- If any required element is missing, respond with:\n"
        "  'I could not generate a Cypher script; the required information is not part of the Neo4j schema.'\n\n"
        "3. Construct the Match Pattern\n"
        "- Use valid node labels and relationships to build MATCH clauses.\n"
        "- Include property filters using WHERE clauses if specified by the user.\n\n"
        "4. Select Return Values\n"
        "- By default, return complete nodes and relationships (e.g., RETURN n1, r, n2).\n"
        "- Only return specific properties if the user requests them explicitly.\n"
        "- Ensure all return elements are valid and defined in the schema.\n\n"
        "5. Generate and Return the Final Cypher Script\n"
        "- Respond with only the final Cypher query. Do not include explanations or formatting.\n"
    )

    try:
        response = client.chat.completions.create(
            model=API_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            temperature=0
        )
        answer = response.choices[0].message.content.strip()
        return {"answer": answer}
    except Exception as e:
        return {"error": str(e)}

# This endpoint uses the OpenAI Assistant API (pre-configured assistant with tools/memory)
# It requires the end developer to set up the assistant in the OpenAI platform,
# then add the OPENAI_ASSISTANT_ID to the .env file in order to use it
@app.post("/api/assistant/ask")
async def ask_assistant(request: QueryRequest):
    user_query = request.query.strip()

    try:
        # Create a new thread
        thread = client.beta.threads.create()

        # Send user's message to the assistant thread
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_query
        )

        # Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=OPENAI_ASSISTANT_ID
        )

        # Wait for completion
        while run.status in ["queued", "in_progress"]:
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        # Get assistant's response
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        
        for message in messages.data:
            if message.role == 'assistant':
                answer = message.content[0].text.value.strip()
                return {"answer": answer}

        return {"answer": "No response from assistant."}

    except Exception as e:
        return {"error": str(e)}