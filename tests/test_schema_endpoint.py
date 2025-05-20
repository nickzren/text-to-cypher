import asyncio
import os
import sys
import types
import unittest

sys.modules.setdefault('dotenv', types.SimpleNamespace(load_dotenv=lambda: None))
sys.modules.setdefault('openai', types.SimpleNamespace(OpenAI=lambda: None))
sys.modules.setdefault(
    'src.text2cypher_agent',
    types.SimpleNamespace(
        Text2CypherAgent=type(
            'Dummy',
            (),
            {
                'respond': lambda self, q: '',
                'get_history': lambda self: [],
                'clear_history': lambda self: None,
            },
        )
    ),
)

os.environ.setdefault('OPENAI_ASSISTANT_ID', 'dummy')
os.environ.setdefault('NEO4J_SCHEMA_PATH', 'data/input/neo4j_schema.json')

import src.api_server as api_server


class SchemaEndpointTest(unittest.TestCase):
    def test_schema_keys(self):
        schema = asyncio.run(api_server.fetch_schema())
        self.assertIn('NodeTypes', schema)
        self.assertIn('RelationshipTypes', schema)


if __name__ == '__main__':
    unittest.main()

