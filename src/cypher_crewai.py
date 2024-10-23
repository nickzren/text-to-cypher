import json
import argparse
from crewai import Agent, Task, Crew, Process
from crewai_tools import FileReadTool
from utils import get_env_variable
from langchain_openai import ChatOpenAI

# Set the path to the Neo4j schema JSON file
neo4j_schema_path = 'data/input/neo4j_schema.json'
cypher_output_path = 'data/output/cypher.txt'

# Set your API keys using the utility function
openai_api_key = get_env_variable('OPENAI_API_KEY')

llm_gpt4o_mini = ChatOpenAI(model_name='gpt-4o-mini', openai_api_key=openai_api_key, temperature=0.0)
llm_gpt4o = ChatOpenAI(model_name='gpt-4o', openai_api_key=openai_api_key, temperature=0.0)

# Create FileReadTool for the Neo4j schema
file_read_tool = FileReadTool(file_path=neo4j_schema_path)

# Create the agents
cypher_generator = Agent(
    role='Cypher Generator',
    goal='Generate a Cypher script based on the provided human query and the Neo4j schema.',
    allow_delegation=True,
    backstory='You are an expert in generating Cypher scripts from provided Neo4j schemas and human queries.',
    tools=[file_read_tool],
    max_iter=3,
    llm=llm_gpt4o
)

syntax_checker = Agent(
    role='Syntax Checker',
    goal='Check the generated Cypher script for syntax errors.',
    allow_delegation=True,
    backstory='You are an expert in Cypher syntax and can identify and correct syntax errors.',
    llm=llm_gpt4o_mini,
)

schema_validator = Agent(
    role='Schema Validator',
    goal='Validate the Cypher script against the provided Neo4j schema.',
    allow_delegation=True,
    backstory='You are an expert in Neo4j schemas and can ensure the query uses the correct node type, relation type, and their properties.',
    tools=[file_read_tool],
    llm=llm_gpt4o_mini
)

# Create tasks for each agent
generate_cypher_task = Task(
    description=(
        'Generate a Neo4j Cypher script based on the human query "{query}" and the provided Neo4j schema. '
        'Ensure that all specified relationships and their properties, nodes, and their properties are correctly mapped to the schema.'
    ),
    expected_output='A Cypher query that represents the given human query and Neo4j schema.',
    agent=cypher_generator
)

check_syntax_task = Task(
    description='Check the Cypher query generated from generate_cypher_task for syntax errors. If correct, return "Pass". If there are errors, briefly describe them.',
    expected_output= 'If no errors, return "Pass". If there are errors, describe them briefly.',
    agent=syntax_checker,
    context=[generate_cypher_task]
)

def save_final_script(task_output):
    output_data = json.loads(task_output.raw)
    if 'final_cypher_script' in output_data:
        with open(cypher_output_path, 'w') as file:
            file.write(output_data['final_cypher_script'])
        print(f"Final Cypher script has been written to {cypher_output_path}.")

validate_schema_task = Task(
    description=(
        'Validate the provided Cypher script against Neo4j schema. '
        "Validation requirements:\n"
        "1. Node Types: Verify that all node types in the Cypher script exist in the schema and are used correctly.\n"
        "2. Node Properties: Ensure that properties used within nodes are defined in the schema for those node types. Pay special attention to properties that might belong to relationships instead of nodes.\n"
        "3. Relationship Types: Verify that all relationship types in the Cypher script exist in the schema and are used correctly.\n"
        "4. Relationship Properties: Ensure that properties used within relationships are defined in the schema for those relationship types. If a property is incorrectly associated with a node rather than a relationship (or vice versa), highlight this as a discrepancy.\n"
        "If there are errors, send task back to CypherGenerator for regeneration."
    ),
    expected_output = 'If no errors, return final_cypher_script in JSON format and stop. If there are errors, describe them briefly.',
    agent=schema_validator,
    context=[generate_cypher_task, check_syntax_task],
    output_format='json',
    callback=save_final_script
)

# Add argument parsing for the query input
parser = argparse.ArgumentParser(description="Generate a Cypher query based on human input.")
parser.add_argument('--query', type=str, required=True, help="The human query to generate a Cypher script for.")
args = parser.parse_args()

# Instantiate your crew with the custom manager agent
crew = Crew(
    agents=[cypher_generator, syntax_checker, schema_validator],
    tasks=[generate_cypher_task, check_syntax_task, validate_schema_task],
    manager_llm=llm_gpt4o_mini,
    process=Process.hierarchical,
    memory=True,
    verbose=True
)

# Kick off the process with the query from the input argument
crew.kickoff(
    inputs={
        'query': args.query
    }
)