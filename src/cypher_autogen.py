import json
import argparse
from autogen import ConversableAgent, GroupChat, GroupChatManager, UserProxyAgent, AssistantAgent
from utils import get_env_variable

# Set your API key using the utility function
openai_api_key = get_env_variable('OPENAI_API_KEY')

# Global LLM configuration for reusability
gpt4o_mini_config = {"config_list": [{"model": "gpt-4o-mini", "api_key": openai_api_key, "temperature": 0.0}]}
gpt4o_config = {"config_list": [{"model": "gpt-4o", "api_key": openai_api_key, "temperature": 0.0}]}

# Set the path to the Neo4j schema JSON file
neo4j_schema_path = 'data/input/neo4j_schema.json'

# Load the schema file
def load_neo4j_schema():
    with open(neo4j_schema_path, 'r') as file:
        return json.load(file)

# Create an Assistant Agent to handle schema loading
schema_loader_assistant = AssistantAgent(
    name="SchemaLoaderAssistant",
    llm_config=gpt4o_mini_config,
    system_message="You are responsible for loading the Neo4j schema from a JSON file. Use the function 'load_neo4j_schema' to load the schema.",
)

schema_loader_assistant.register_for_llm(name="load_neo4j_schema", description="Loads the Neo4j schema")(load_neo4j_schema)

# Define the Cypher Generator
cypher_generator = ConversableAgent(
    name="CypherGenerator",
    system_message=(
        "You are an expert in generating Cypher scripts based on provided human query.\n"
        "Based on this query and the provided Neo4j schema, generate a Cypher query that strictly follows the requirements of the human query. "
        "Do not add any additional filters, conditions, or logic that is not explicitly stated in the human query. Adhere closely to the schema provided schema\n"
        "If you receive feedback on your generated script, use that feedback to regenerate and improve the script."
        "Only generate the Cypher script without any explanations or additional comments."
    ),
    llm_config=gpt4o_config,
    human_input_mode="NEVER",
)

# Define the Syntax Checker
syntax_checker = ConversableAgent(
    name="SyntaxChecker",
    system_message=(
        "You are an expert in Cypher syntax. To check provided Cypher script.\n"
        "If no syntax errors, return 'Syntax Check Pass'. Otherwise, briefly describe the issues."
    ),
    llm_config=gpt4o_mini_config,
    human_input_mode="NEVER",
)

# Define the Schema Validator
schema_validator = ConversableAgent(
    name="SchemaValidator",
    system_message=(
        "You are an expert in validating provided Cypher scripts against the Neo4j schema.\n"
        "Validation requirements:\n"
        "1. Node Types: Verify that all node types in the Cypher script exist in the schema and are used correctly.\n"
        "2. Node Properties: Ensure that properties used within nodes are defined in the schema for those node types. Pay special attention to properties that might belong to relationships instead of nodes.\n"
        "3. Relationship Types: Verify that all relationship types in the Cypher script exist in the schema and are used correctly.\n"
        "4. Relationship Properties: Ensure that properties used within relationships are defined in the schema for those relationship types. If a property is incorrectly associated with a node rather than a relationship (or vice versa), highlight this as a discrepancy.\n"
        "5. Discrepancies: Highlight any discrepancies where a property is incorrectly associated with a node or a relationship.\n"
        "If the script is valid, return 'Schema Validation PASS' and final Cypher script. Otherwise, briefly describe the issues as feedback."
    ),
    llm_config=gpt4o_config,
    human_input_mode="NEVER",
)

# Define the Manager with updated termination condition
manager = UserProxyAgent(
    name="Manager",
    system_message=(
        "You are the manager overseeing the generation and validation of a Cypher script.\n"
        "Get the Neo4j schema using the SchemaLoaderAssistant and only do it once for reuse.\n"
        "Your task is to:\n"
        "1. Send human query and schema to CypherGenerator for cypher generation.\n"
        "2. Send the generated script to the SyntaxChecker for syntax validation.\n"
        "3. If the SyntaxChecker returns 'Syntax Check Pass', send the script and schema to the SchemaValidator for schema validation.\n"
        "4. If the SyntaxChecker finds errors, send the feedback and task back to the CypherGenerator to regenerate the script.\n"
        "5. If the SchemaValidator returns 'Schema Validation PASS', terminate the process and print the final script.\n"
        "6. If the SchemaValidator finds errors, send the feedback and task back to the CypherGenerator for regeneration."
    ),
    llm_config=gpt4o_mini_config,
    human_input_mode="NEVER",
    is_termination_msg=lambda message: "Schema Validation PASS" in message["content"],
    code_execution_config=False
)

manager.register_for_execution(name="load_neo4j_schema")(load_neo4j_schema)

# Define the Group Chat with restricted speaker transitions
groupchat = GroupChat(
    agents=[manager, schema_loader_assistant, cypher_generator, syntax_checker, schema_validator],
    messages=[],
    allowed_or_disallowed_speaker_transitions={
        manager: [schema_loader_assistant, cypher_generator, syntax_checker, schema_validator],
        schema_loader_assistant: [manager],
        cypher_generator: [manager],
        syntax_checker: [manager],
        schema_validator: [manager],
    },
    speaker_transitions_type="allowed",
)

# Create the Group Chat Manager
groupchat_manager = GroupChatManager(
    groupchat=groupchat,
    llm_config=gpt4o_mini_config,
)

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Generate Cypher query based on human input.")
parser.add_argument("--query", type=str, required=True, help="The human query to generate a Cypher script for.")
args = parser.parse_args()

# Start the Group Chat by asking the Manager to initiate the process
groupchat_result = manager.initiate_chat(
    groupchat_manager,
    message=f"Get Neo4j schema, then generate Cypher query for the following human query:\n\n{args.query}",
)

summary = groupchat_result.summary
# Extract the final Cypher script block
final_script = summary.split("```cypher")[-1].split("```")[0].strip()
print(final_script, "\n")
print("Cost info:", groupchat_result.cost)