import asyncio
import time
import unittest
import types
import sys

sys.modules.setdefault('dotenv', types.SimpleNamespace(load_dotenv=lambda: None))
sys.modules.setdefault('openai', types.SimpleNamespace(OpenAI=lambda: None))
sys.modules.setdefault('src.text2cypher_agent', types.SimpleNamespace(Text2CypherAgent=type('Dummy', (), {'respond': lambda self, q: '', 'get_history': lambda self: [], 'clear_history': lambda self: None})))

import src.api_server as api_server

class FakeMessages:
    def __init__(self, store):
        self.store = store
    def create(self, *, thread_id, role, content):
        self.store.setdefault('messages', []).append(content)
    def list(self, *, thread_id):
        content = self.store.get('messages', []).pop(0)
        msg = type('Msg', (), {
            'role': 'assistant',
            'content': [type('Cont', (), {
                'text': type('Val', (), {'value': f'answer to {content}'})()
            })]
        })
        return type('Msgs', (), {'data': [msg]})

class FakeRuns:
    def create(self, *, thread_id, assistant_id):
        return type('Run', (), {'id': 'run', 'status': 'queued'})
    def retrieve(self, *, thread_id, run_id):
        time.sleep(0.1)
        return type('Run', (), {'id': run_id, 'status': 'completed'})

class FakeThreads:
    def __init__(self):
        self.store = {}
        self.messages = FakeMessages(self.store)
        self.runs = FakeRuns()
    def create(self):
        return type('Thread', (), {'id': 'thread'})

class FakeBeta:
    def __init__(self):
        self.threads = FakeThreads()

class FakeClient:
    def __init__(self):
        self.beta = FakeBeta()

class ConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.old_client = api_server.client
        api_server.client = FakeClient()
        api_server._REMOTE_THREAD_ID = None

    def tearDown(self):
        api_server.client = self.old_client
        api_server._REMOTE_THREAD_ID = None

    async def _call(self, text):
        req = api_server.QueryRequest(query=text)
        return await api_server.ask_remote_agent(req)

    def test_multiple_requests(self):
        async def gather():
            return await asyncio.gather(self._call('q0'), self._call('q1'))

        start = time.perf_counter()
        results = asyncio.run(gather())
        elapsed = time.perf_counter() - start
        answers = [r['answer'] for r in results]
        self.assertEqual(answers, ['answer to q0', 'answer to q1'])
        self.assertLess(elapsed, 1.5)

if __name__ == '__main__':
    unittest.main()
