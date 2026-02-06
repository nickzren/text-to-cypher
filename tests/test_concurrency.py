import asyncio
import time
import unittest
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.api_server as api_server
from src.text2cypher_agent import Text2CypherAgent


class SlowAgent:
    def respond(self, query: str, session_id: str) -> str:
        time.sleep(0.25)
        return f"RETURN '{query}' AS q"


class ConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        Text2CypherAgent.clear_session_history()
        api_server._SESSION_RUN_LOCKS.clear()
        api_server._SESSION_RUN_LAST_USED.clear()
        self._old_max_session_run_locks = api_server.MAX_SESSION_RUN_LOCKS

    async def asyncTearDown(self):
        Text2CypherAgent.clear_session_history()
        api_server._SESSION_RUN_LOCKS.clear()
        api_server._SESSION_RUN_LAST_USED.clear()
        api_server.MAX_SESSION_RUN_LOCKS = self._old_max_session_run_locks

    async def test_llm_requests_run_concurrently_across_sessions(self):
        req0 = api_server.QueryRequest(query="q0", session_id="s1", provider="openai")
        req1 = api_server.QueryRequest(query="q1", session_id="s2", provider="openai")

        start = time.perf_counter()
        with patch(
            "src.api_server.get_or_create_agent",
            AsyncMock(return_value=SlowAgent()),
        ):
            results = await asyncio.gather(
                api_server.ask_llm_agent(req0),
                api_server.ask_llm_agent(req1),
            )
        elapsed = time.perf_counter() - start

        answers = [r["answer"] for r in results]
        self.assertEqual(answers, ["RETURN 'q0' AS q", "RETURN 'q1' AS q"])
        self.assertLess(elapsed, 0.45)

    async def test_llm_requests_are_serialized_within_session(self):
        req0 = api_server.QueryRequest(query="q0", session_id="same", provider="openai")
        req1 = api_server.QueryRequest(query="q1", session_id="same", provider="openai")

        start = time.perf_counter()
        with patch(
            "src.api_server.get_or_create_agent",
            AsyncMock(return_value=SlowAgent()),
        ):
            await asyncio.gather(
                api_server.ask_llm_agent(req0),
                api_server.ask_llm_agent(req1),
            )
        elapsed = time.perf_counter() - start

        self.assertGreater(elapsed, 0.45)

    async def test_history_isolated_by_session(self):
        Text2CypherAgent.append_external_exchange("session_a", "user_a", "assistant_a")
        Text2CypherAgent.append_external_exchange("session_b", "user_b", "assistant_b")

        history_a = await api_server.get_shared_history("session_a")
        history_b = await api_server.get_shared_history("session_b")

        self.assertEqual(len(history_a["history"]), 2)
        self.assertEqual(len(history_b["history"]), 2)
        self.assertEqual(history_a["history"][0]["content"], "user_a")
        self.assertEqual(history_b["history"][0]["content"], "user_b")

    async def test_session_lock_not_evicted_for_new_session(self):
        api_server.MAX_SESSION_RUN_LOCKS = 2

        lock_s1 = await api_server.get_session_run_lock("s1")
        lock_s2 = await api_server.get_session_run_lock("s2")
        await lock_s1.acquire()
        await lock_s2.acquire()
        try:
            lock_s3_first = await api_server.get_session_run_lock("s3")
            self.assertIs(api_server._SESSION_RUN_LOCKS.get("s3"), lock_s3_first)

            lock_s3_second = await api_server.get_session_run_lock("s3")
            self.assertIs(lock_s3_first, lock_s3_second)
        finally:
            lock_s1.release()
            lock_s2.release()

    async def test_clear_waits_for_inflight_session_write(self):
        session_id = "race_session"

        async def inflight_write():
            session_lock = await api_server.get_session_run_lock(session_id)
            async with session_lock:
                await asyncio.sleep(0.05)
                Text2CypherAgent.append_external_exchange(session_id, "u", "a")

        write_task = asyncio.create_task(inflight_write())
        await asyncio.sleep(0.01)
        await api_server.clear_shared_history(api_server.SessionRequest(session_id=session_id))
        await write_task

        history = Text2CypherAgent.get_session_history(session_id)
        self.assertEqual(history, [])


if __name__ == "__main__":
    unittest.main()
