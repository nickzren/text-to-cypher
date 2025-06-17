import argparse
import json
from pathlib import Path
from neo4j import GraphDatabase
from utils import get_env_variable
import sys

def _sort_schema(d: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    """
    Return a new mapping where the top‑level keys and each nested property
    map are sorted alphabetically.  Helps guarantee deterministic JSON
    output when the database hasn’t changed.
    """
    return {lbl: dict(sorted(props.items())) for lbl, props in sorted(d.items())}

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

        # sort keys for deterministic output
        node_schema = _sort_schema(node_schema)
        rel_schema  = _sort_schema(rel_schema)

    schema = {"NodeTypes": node_schema, "RelationshipTypes": rel_schema}
    out_path = output_dir / "neo4j_schema.json"
    json_str = json.dumps(schema, indent=2, sort_keys=True)
    out_path.write_text(json_str)
    print(f"Schema dumped → {out_path}")


def get_node_schema(session):
    """
    Return a dict[label -> {property -> type}] that includes *all* labels,
    even when no nodes for that label currently store properties.
    """
    # 1) gather property definitions
    q_props = """
    CALL db.schema.nodeTypeProperties()
    YIELD nodeType, propertyName, propertyTypes
    RETURN nodeType, propertyName, propertyTypes
    """
    schema: dict[str, dict[str, str]] = {}
    for rec in session.run(q_props):
        label = rec["nodeType"].strip(":`")
        prop  = rec["propertyName"]
        types_list = rec["propertyTypes"] or []
        types = ", ".join(types_list) if types_list else "Unknown"
        schema.setdefault(label, {})[prop] = types

    # 2) make sure labels with *no* properties are still represented
    q_labels = "CALL db.labels() YIELD label RETURN label"
    for rec in session.run(q_labels):
        label = rec["label"]
        schema.setdefault(label, {})  # leave value dict empty

    return schema


def get_relationship_schema(session):
    """
    For each relationship type return its property map and a sampled endpoint
    pair.  Includes relationship types that have zero properties.
    """
    rel_schema: dict[str, dict[str, str]] = {}

    # 1) property definitions (may return zero rows for prop‑less rel‑types)
    q_props = """
    CALL db.schema.relTypeProperties()
    YIELD relType, propertyName, propertyTypes
    RETURN relType, propertyName, propertyTypes
    """
    for rec in session.run(q_props):
        rtype = rec["relType"].strip(":`")
        prop  = rec["propertyName"]
        rel_schema.setdefault(rtype, {})          # ensure the key exists
        if prop:
            types_list = rec["propertyTypes"] or []
            types = ", ".join(types_list) if types_list else "Unknown"
            rel_schema[rtype][prop] = types

    # 2) add rel‑types that have *no* properties at all
    q_all = "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
    for rec in session.run(q_all):
        rtype = rec["relationshipType"]
        rel_schema.setdefault(rtype, {})

    # 3) sample endpoints for every relationship type
    for rtype in rel_schema:
        q_sample = f'''
        MATCH (s)-[r:`{rtype}`]->(t)
        WITH head(labels(s)) AS src, head(labels(t)) AS tgt, elementId(r) AS rid
        ORDER BY rid
        RETURN src, tgt
        LIMIT 1
        '''
        rec = session.run(q_sample).single()
        if rec:
            rel_schema[rtype]["_endpoints"] = [rec["src"], rec["tgt"]]
        else:
            rel_schema[rtype]["_endpoints"] = ["Unknown", "Unknown"]

    return rel_schema


if __name__ == "__main__":
    main()