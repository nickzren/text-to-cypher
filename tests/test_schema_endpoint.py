import asyncio
import os
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.api_server as api_server
import src.schema_loader as schema_loader


class SchemaEndpointTest(unittest.TestCase):
    def test_schema_keys(self):
        schema = asyncio.run(api_server.fetch_schema())
        self.assertIn("NodeTypes", schema)
        self.assertIn("RelationshipTypes", schema)

    def test_schema_hints_path_is_optional(self):
        old_cached_hints = schema_loader._cached_hints
        old_hints_loaded = schema_loader._hints_loaded
        try:
            schema_loader._cached_hints = None
            schema_loader._hints_loaded = False
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("SCHEMA_HINTS_PATH", None)
                self.assertIsNone(schema_loader.get_schema_hints())
        finally:
            schema_loader._cached_hints = old_cached_hints
            schema_loader._hints_loaded = old_hints_loaded

    def test_session_id_validation(self):
        with self.assertRaises(ValidationError):
            api_server.QueryRequest(query="q", session_id="bad id")

    def test_query_max_length_validation(self):
        with self.assertRaises(ValidationError):
            api_server.QueryRequest(
                query="x" * (api_server.MAX_QUERY_LENGTH + 1),
                session_id="ok-session",
            )


if __name__ == "__main__":
    unittest.main()
