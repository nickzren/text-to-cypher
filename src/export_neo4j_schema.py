# src/dump_schema.py
import os
import argparse
import json
from pathlib import Path
from neo4j import GraphDatabase
from utils import get_env_variable
import sys

def main():
    parser = argparse.ArgumentParser(description="Export Neo4j schema.")
    parser.add_argument("--output_dir", required=True, help="Path to store neo4j_schema.json")
    args = parser.parse_args()

    try:
        uri = get_env_variable("DB_URL")
        db_name = get_env_variable("DB_NAME")
    except EnvironmentError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1)

    # ---- auth (uncomment if needed) ----
    # user     = get_env_variable("DB_USER")
    # password = get_env_variable("DB_PASSWORD")
    # driver   = GraphDatabase.driver(uri, auth=(user, password))
    driver   = GraphDatabase.driver(uri, auth=None)

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with driver.session(database=db_name) as session:
        node_schema = get_node_schema(session)
        rel_schema  = get_relationship_schema(session)

    schema = {"NodeTypes": node_schema, "RelationshipTypes": rel_schema}
    out_path = output_dir / "neo4j_schema.json"
    out_path.write_text(json.dumps(schema, indent=2))
    print(f"Schema dumped → {out_path}")

# ----------------------------------------------------------------------
def get_node_schema(session):
    q = """
    CALL db.schema.nodeTypeProperties()
    YIELD nodeType, propertyName, propertyTypes
    RETURN nodeType, propertyName, propertyTypes
    """
    schema = {}
    for rec in session.run(q):
        label = rec["nodeType"].strip(":`")
        prop  = rec["propertyName"]
        types = ", ".join(rec["propertyTypes"]) or "Unknown"
        schema.setdefault(label, {})[prop] = types
    return schema

# ----------------------------------------------------------------------
def get_relationship_schema(session):
    """
    For each relType: collect property definitions + a sampled (srcLabel, tgtLabel).
    """
    # 1) property map
    q_props = """
    CALL db.schema.relTypeProperties()
    YIELD relType, propertyName, propertyTypes
    RETURN relType, propertyName, propertyTypes
    """
    rel_schema = {}
    for rec in session.run(q_props):
        rtype = rec["relType"].strip(":`")
        prop  = rec["propertyName"]
        if prop:
            types = ", ".join(rec["propertyTypes"]) or "Unknown"
            rel_schema.setdefault(rtype, {})[prop] = types

    # 2) sample endpoints for each relationship type
    for rtype in rel_schema:
        q_sample = f"""
        MATCH (s)-[r:`{rtype}`]->(t)
        WITH labels(s)[0] AS src, labels(t)[0] AS tgt
        RETURN src, tgt LIMIT 1
        """
        rec = session.run(q_sample).single()
        if rec:
            rel_schema[rtype]["_endpoints"] = [rec["src"], rec["tgt"]]
        else:  # no relationship instance found
            rel_schema[rtype]["_endpoints"] = ["Unknown", "Unknown"]

    return rel_schema

# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()