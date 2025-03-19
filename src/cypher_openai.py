import asyncio
import uuid
import os
import json
import argparse
from dataclasses import dataclass
from pydantic import BaseModel, ValidationError
from utils import get_env_variable
from openai.types.responses import ResponseContentPartDoneEvent, ResponseTextDeltaEvent
from agents import Agent, RunContextWrapper, function_tool
from agents import RawResponsesStreamEvent, Runner, TResponseInputItem, trace

os.environ["OPENAI_API_KEY"] = get_env_variable("OPENAI_API_KEY")

@dataclass
class AppContext:
    """Local context for the run, storing the Neo4j schema in memory."""
    neo4j_schema: dict

@function_tool
def load_neo4j_schema(wrapper: RunContextWrapper[AppContext]) -> dict:
    """
    Returns the cached Neo4j schema from the local context.
    No file reading; it uses the schema already stored in wrapper.context.
    """
    return wrapper.context.neo4j_schema

class Output(BaseModel):
    status: bool     # True/False pass/fail
    cypher: str      # The current Cypher query
    feedback: str    # Reason for failure, or empty string if pass

cypher_generator_agent = Agent[AppContext](
    name="cypher_generator_agent",
    instructions=(
        "You are the Cypher Generator.\n\n"
        "Behavior:\n"
        "1) You receive the user's request (plus optional feedback).\n"
        "2) You ALWAYS output JSON matching the Output schema exactly:\n\n"
        "   {\n"
        "       \"status\": true,\n"
        "       \"cypher\": \"...\",\n"
        "       \"feedback\": \"\"\n"
        "   }\n\n"
        "   - 'status' is always true here.\n"
        "   - 'cypher' is your newly generated or revised Cypher.\n"
        "   - 'feedback' is always empty.\n\n"
        "3) If you want to see the schema, call `load_neo4j_schema` (no arguments).\n"
        "4) End your output with no extra text.\n"
    ),
    output_type=Output,
    tools=[load_neo4j_schema],
    handoffs=[]
)

syntax_checker_agent = Agent[AppContext](
    name="syntax_checker_agent",
    instructions=(
        "You are the Syntax Checker.\n\n"
        "Behavior:\n"
        "1) You receive an Output JSON from cypher_generator_agent.\n"
        "2) Validate the 'cypher' for syntax correctness.\n"
        "3) Return JSON matching the Output schema exactly:\n"
        "   - 'status': true if syntax pass, false if syntax fail.\n"
        "   - 'cypher': the same cypher.\n"
        "   - 'feedback': reason for fail, or \"\" if pass.\n\n"
        "If status=false, we go back to cypher_generator_agent with your feedback.\n"
        "If status=true, we move on to schema_validator_agent.\n\n"
        "You do NOT need the schema to check syntax, so no tools.\n"
        "End your output with no extra text.\n"
    ),
    output_type=Output,
    tools=[],
    handoffs=[]
)

schema_validator_agent = Agent[AppContext](
    name="schema_validator_agent",
    instructions=(
        "You are the Schema Validator.\n\n"
        "Behavior:\n"
        "1) You receive an Output JSON from syntax_checker_agent.\n"
        "2) If needed, call `load_neo4j_schema` (no arguments) to retrieve the schema.\n"
        "3) Validate the 'cypher' against the schema.\n"
        "4) Return JSON matching the Output schema exactly:\n"
        "   - 'status': true if schema pass, false if schema fail.\n"
        "   - 'cypher': the same cypher.\n"
        "   - 'feedback': reason for fail, or \"\" if pass.\n\n"
        "If status=false, we go back to cypher_generator_agent with feedback.\n"
        "If status=true, the chain ends.\n\n"
        "End your output with no extra text.\n"
    ),
    output_type=Output,
    tools=[load_neo4j_schema],
    handoffs=[]
)

cypher_generator_agent.handoffs = [syntax_checker_agent, schema_validator_agent]
syntax_checker_agent.handoffs   = [cypher_generator_agent, schema_validator_agent]
schema_validator_agent.handoffs = [cypher_generator_agent]

async def generate_cypher(human_query: str, schema_data: dict) -> str:
    """
    Main chain of events:
      1) cypher_generator_agent => Output(status=True) => next
      2) syntax_checker_agent => pass => schema_validator_agent or fail => back
      3) schema_validator_agent => pass => done or fail => back
    """
    conversation_id = str(uuid.uuid4().hex[:16])
    max_iterations = 10

    # Create the context object with the full schema loaded:
    app_context = AppContext(neo4j_schema=schema_data)

    with trace("Text to Cypher", group_id=conversation_id):
        current_agent = cypher_generator_agent
        iteration_count = 0

        # Start with a user message
        user_message = (
            f"User Query: {human_query}\n\n"
            "No feedback for now. Produce an Output JSON with status=true.\n"
            "If needed, call `load_neo4j_schema` with no arguments to see the schema."
        )

        while iteration_count < max_iterations:
            iteration_count += 1

            inputs: list[TResponseInputItem] = [{
                "content": user_message,
                "role": "user"
            }]

            # Provide the context to the runner
            result = Runner.run_streamed(current_agent, input=inputs, context=app_context)
            partial_text_chunks = []
            async for event in result.stream_events():
                if isinstance(event, RawResponsesStreamEvent):
                    data = event.data
                    if isinstance(data, ResponseTextDeltaEvent):
                        partial_text_chunks.append(data.delta)
                    elif isinstance(data, ResponseContentPartDoneEvent):
                        pass

            full_output_str = "".join(partial_text_chunks).strip()
            print(f"--- {current_agent.name} output ---\n{full_output_str}\n")

            # Parse the agent's output as JSON matching Output
            try:
                parsed_json = json.loads(full_output_str)
                agent_output = Output(**parsed_json)
            except (json.JSONDecodeError, ValidationError) as e:
                print(f"Error parsing {current_agent.name} output: {e}")
                return ""

            # If schema_validator_agent => pass => done
            if current_agent == schema_validator_agent and agent_output.status:
                return agent_output.cypher

            # Decide next agent
            if agent_output.status:
                # pass => move forward
                if current_agent == cypher_generator_agent:
                    current_agent = syntax_checker_agent
                elif current_agent == syntax_checker_agent:
                    current_agent = schema_validator_agent
                user_message = full_output_str
            else:
                # fail => go back to generator
                current_agent = cypher_generator_agent
                user_message = (
                    "Here's the last Output JSON (fail). Please revise your Cypher:\n"
                    + full_output_str
                )

        print("Max iterations reached, no final success.")
        return ""

async def main():
    parser = argparse.ArgumentParser(description="Generate a validated Cypher query with minimal schema exposure.")
    parser.add_argument("--query", type=str, required=True, help="Human query for Cypher generation.")
    parser.add_argument(
        "--schema_file",
        type=str,
        default="data/input/neo4j_schema.json",
        help="Path to the Neo4j schema JSON file."
    )
    args = parser.parse_args()

    with open(args.schema_file, "r") as f:
        schema_data = json.load(f)

    final_cypher = await generate_cypher(args.query, schema_data)
    if final_cypher:
        print("Final Cypher:\n", final_cypher)


if __name__ == "__main__":
    asyncio.run(main())