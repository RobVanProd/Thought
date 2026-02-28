import unittest
from unittest.mock import patch

from thought_wrapper.sdk.clients import (
    AnthropicClient,
    LlamaCppClient,
    OllamaClient,
    OpenAIClient,
    XAIClient,
)


class TestSdkClients(unittest.TestCase):
    def test_openai_client_success(self) -> None:
        with patch("thought_wrapper.sdk.clients._http_json") as mock_http:
            mock_http.return_value = {"choices": [{"message": {"content": "openai-ok"}}]}
            client = OpenAIClient(api_key="k-test")
            out = client.complete(
                system_prompt="sys",
                user_prompt="user",
                model="gpt-test",
                temperature=0.2,
                max_tokens=128,
            )
            self.assertEqual(out, "openai-ok")

    def test_openai_client_missing_key(self) -> None:
        client = OpenAIClient(api_key=None)
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError):
                client.complete(
                    system_prompt="sys",
                    user_prompt="user",
                    model="gpt-test",
                    temperature=0.2,
                    max_tokens=128,
                )

    def test_anthropic_client_success(self) -> None:
        with patch("thought_wrapper.sdk.clients._http_json") as mock_http:
            mock_http.return_value = {"content": [{"type": "text", "text": "anthropic-ok"}]}
            client = AnthropicClient(api_key="k-test")
            out = client.complete(
                system_prompt="sys",
                user_prompt="user",
                model="claude-test",
                temperature=0.2,
                max_tokens=128,
            )
            self.assertEqual(out, "anthropic-ok")

    def test_xai_client_success(self) -> None:
        with patch("thought_wrapper.sdk.clients._http_json") as mock_http:
            mock_http.return_value = {"choices": [{"message": {"content": "xai-ok"}}]}
            client = XAIClient(api_key="k-test")
            out = client.complete(
                system_prompt="sys",
                user_prompt="user",
                model="grok-test",
                temperature=0.2,
                max_tokens=128,
            )
            self.assertEqual(out, "xai-ok")

    def test_ollama_client_success(self) -> None:
        with patch("thought_wrapper.sdk.clients._http_json") as mock_http:
            mock_http.return_value = {"message": {"content": "ollama-ok"}}
            client = OllamaClient(base_url="http://localhost:11434")
            out = client.complete(
                system_prompt="sys",
                user_prompt="user",
                model="llama3.1",
                temperature=0.2,
                max_tokens=128,
            )
            self.assertEqual(out, "ollama-ok")

    def test_llamacpp_client_success(self) -> None:
        with patch("thought_wrapper.sdk.clients._http_json") as mock_http:
            mock_http.return_value = {"choices": [{"message": {"content": "llamacpp-ok"}}]}
            client = LlamaCppClient(base_url="http://localhost:8080/v1")
            out = client.complete(
                system_prompt="sys",
                user_prompt="user",
                model="local-model",
                temperature=0.2,
                max_tokens=128,
            )
            self.assertEqual(out, "llamacpp-ok")


if __name__ == "__main__":
    unittest.main()
