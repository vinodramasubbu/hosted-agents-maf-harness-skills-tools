import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch

from azure.core.exceptions import AzureError

import demo_server
import test as client


class ClientTests(unittest.TestCase):
    @patch.object(client, "AIProjectClient")
    @patch.object(client, "DefaultAzureCredential")
    def test_returns_output_and_cleans_up(self, credential, project_factory):
        project = project_factory.return_value.__enter__.return_value
        project.agents.create_session.return_value.agent_session_id = "mock-session"
        openai = project.get_openai_client.return_value.__enter__.return_value
        openai.responses.create.return_value = SimpleNamespace(
            output_text="Example answer",
            output=[
                SimpleNamespace(type="function_call", name="load_skill", arguments='{"skill_name":"etf-analysis"}'),
                SimpleNamespace(type="function_call", name="fetch_market_data", arguments='{"ticker":"QQQM"}'),
            ],
        )
        output = client.run_question(" Compare ETFs ")
        self.assertIn("Example answer", output)
        self.assertIn("etf-analysis", output)
        self.assertIn("fetch_market_data", output)
        openai.responses.create.assert_called_once_with(
            input="Compare ETFs", extra_body={"agent_session_id": "mock-session"},
        )
        project.agents.delete_session.assert_called_once_with(
            agent_name=client.agent_name, session_id="mock-session",
        )

    @patch.object(client, "AIProjectClient")
    @patch.object(client, "DefaultAzureCredential")
    def test_cleanup_on_provider_failure(self, credential, project_factory):
        project = project_factory.return_value.__enter__.return_value
        project.agents.create_session.return_value.agent_session_id = "mock-session"
        project.get_openai_client.return_value.__enter__.return_value.responses.create.side_effect = AzureError("failure")
        with self.assertRaises(AzureError):
            client.run_question("Analyze MSFT")
        project.agents.delete_session.assert_called_once()

    def test_invalid_questions_do_not_invoke(self):
        with patch.object(client, "AIProjectClient") as project:
            for value in ("", " ", "x" * 4001, None):
                with self.assertRaises(ValueError):
                    client.run_question(value)
            project.assert_not_called()


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), demo_server.DemoHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        try:
            connection.request(method, path, body, headers or {})
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_page_and_health(self):
        status, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Ask agent", body)
        self.assertEqual(self.request("GET", "/health")[0], 200)
        self.assertEqual(self.request("GET", "/test.py")[0], 404)

    @patch.object(demo_server, "run_question", return_value="Example answer")
    def test_invocation_and_input_guards(self, invoke):
        headers = {"Content-Type": "application/json"}
        status, body = self.request("POST", "/api/ask", json.dumps({"question": "Analyze MSFT"}), headers)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["output"], "Example answer")
        invoke.assert_called_once_with("Analyze MSFT")
        invoke.reset_mock()
        for body in ('{"question":""}', '{"question":5}', "null", "{"):
            self.assertEqual(self.request("POST", "/api/ask", body, headers)[0], 400)
        self.assertEqual(self.request("POST", "/api/ask", "x", {"Content-Type": "text/plain"})[0], 415)
        foreign = {**headers, "Origin": "https://example.com"}
        self.assertEqual(self.request("POST", "/api/ask", "{}", foreign)[0], 403)
        self.assertEqual(self.request("GET", "/", headers={"Host": "example.com"})[0], 403)
        invoke.assert_not_called()

    @patch.object(demo_server, "run_question", side_effect=AzureError("secret must not be returned"))
    def test_provider_failure_is_explicit_and_sanitized(self, invoke):
        status, body = self.request(
            "POST", "/api/ask", '{"question":"Analyze MSFT"}', {"Content-Type": "application/json"},
        )
        self.assertEqual(status, 502)
        self.assertIn(b"AzureError", body)
        self.assertNotIn(b"secret must not be returned", body)
        self.assertTrue(demo_server.RUN_LOCK.acquire(blocking=False))
        demo_server.RUN_LOCK.release()


if __name__ == "__main__":
    unittest.main()
