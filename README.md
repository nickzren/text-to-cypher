# text-to-cypher
A lightweight AI agent-based framework that converts natural language queries into Cypher scripts for Neo4j, leveraging LLMs for precise query generation.

### Prerequisites

- Git
- Miniconda (with Mamba)

### Setup

1. Clone the repository:
   ```sh
   git clone git@github.com:nickzren/text-to-cypher.git
   ```
2. Initialize conda environment:
   ```sh
   cd text-to-cypher
   mamba env create -f environment.yml
   ```
3. Update the `.env` file to set `OPENAI_API_KEY`.

### Run

1. Init environment:
   ```sh
   cd text-to-cypher
   conda activate text-to-cypher
   ```
2. Run example scripts:
   ```sh
   # openai framework
   python src/cypher_openai.py --query "Show compounds that treat both type 2 diabetes mellitus and hypertension."

   # autogen framework
   python src/cypher_autogen.py --query "Show compounds that treat both type 2 diabetes mellitus and hypertension."

   # crewai framework
   python src/cypher_crewai.py --query "Find all genes that participate in the mitotic spindle checkpoint and are expressed in the lung."
   ```

### Data

The file `data/input/neo4j_schema.json` contains a Neo4j schema dump. While the example uses the Hetionet Neo4j database, the dump_neo4j_schema.py script can be used to dump the schema from **any** Neo4j database.

To set up the Hetionet Neo4j Docker container locally, follow the instructions from [this link](https://github.com/nickzren/hetionet/tree/main?tab=readme-ov-file#docker-setup-and-initialization).

If you need to dump the schema from your own Neo4j instance, first update the `.env` file to set `DB_URL` and `DB_NAME`.

Then, run the following command to dump the schema:
```sh
python src/dump_neo4j_schema.py --output_dir data/input/
```

You can also access the Neo4j Browser at http://localhost:7474 to run the Cypher queries generated by the text-to-cypher framework.