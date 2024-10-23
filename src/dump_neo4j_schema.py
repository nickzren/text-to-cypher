import os
import argparse
import json
from neo4j import GraphDatabase
from utils import get_env_variable

# Function to export Neo4j schema to JSON
def export_schema_as_json(output_dir):
    query = """
    CALL {
      MATCH (n1)-[r]->(n2)
      WITH DISTINCT labels(n1) AS sourceNodeLabels, type(r) AS relationshipType, labels(n2) AS targetNodeLabels, keys(r) AS relationshipProperties
      UNWIND sourceNodeLabels AS sourceLabel
      UNWIND targetNodeLabels AS targetLabel
      UNWIND relationshipProperties AS relProp
      RETURN 'Relationship' AS ElementType, relationshipType AS Type, sourceLabel AS SourceNode, targetLabel AS TargetNode, collect(DISTINCT relProp) AS PropertyFields
      UNION
      MATCH (n)
      WITH DISTINCT labels(n) AS nodeLabels, keys(n) AS properties
      UNWIND nodeLabels AS label
      UNWIND properties AS prop
      RETURN 'Node' AS ElementType, label AS Type, null AS SourceNode, null AS TargetNode, collect(DISTINCT prop) AS PropertyFields
    }
    RETURN ElementType, Type, SourceNode, TargetNode, PropertyFields
    ORDER BY ElementType, Type
    """

    # Get DB connection details from .env file
    uri = get_env_variable('DB_URL')
    db_name = get_env_variable('DB_NAME')

    # Connect to the Neo4j database without authentication (no username or password)
    driver = GraphDatabase.driver(uri, auth=None)

    with driver.session(database=db_name) as session:
        result = session.run(query)
        data = {
            "nodes": [],
            "relationships": []
        }

        # Process query result
        for record in result:
            element_type = record["ElementType"]
            if element_type == "Node":
                data["nodes"].append({
                    "label": record["Type"],
                    "properties": record["PropertyFields"]
                })
            elif element_type == "Relationship":
                data["relationships"].append({
                    "type": record["Type"],
                    "sourceNode": record["SourceNode"],
                    "targetNode": record["TargetNode"],
                    "properties": record["PropertyFields"]
                })
    
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Save to JSON file
    output_file = os.path.join(output_dir, "neo4j_schema.json")
    with open(output_file, "w") as outfile:
        json.dump(data, outfile, indent=4)

    print(f"Schema data exported to '{output_file}'.")

def main():
    parser = argparse.ArgumentParser(description='Dump Neo4j schema.')
    parser.add_argument('--output_dir', type=str, required=True, help='Output directory path')
    args = parser.parse_args()

    # Call the function to export schema as JSON
    export_schema_as_json(args.output_dir)

if __name__ == '__main__':
    main()