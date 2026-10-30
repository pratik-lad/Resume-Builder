"""Contract checks for the native GGUF API adapter."""
from unittest.mock import MagicMock, Mock, patch

from llm import client


def test_native_chat_preserves_generation_controls():
    response = Mock()
    response.json.return_value = {
        "choices": [{"message": {"content": '{"answer":"ready"}'}}],
        "timings": {"prompt_n": 12, "predicted_n": 8, "predicted_per_second": 25},
    }
    transport = Mock()
    transport.post.return_value = response
    context = MagicMock()
    context.__enter__.return_value = transport
    schema = {"type": "object", "properties": {"answer": {"type": "string"}}}

    with patch.object(client.httpx, "Client", return_value=context), patch.object(
        client.settings, "llm_api_key", "test-key"
    ):
        text = client.chat("Return JSON", system="system", fmt=schema,
                           temperature=0.15, num_predict=3500)

    body = transport.post.call_args.kwargs["json"]
    assert text == '{"answer":"ready"}'
    assert body["response_format"] == {"type": "json_schema", "schema": schema}
    assert body["max_tokens"] == 3500
    assert body["reasoning_effort"] == "none"
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    assert body["temperature"] == 0.15
    assert body["top_p"] == client.settings.top_p
    assert body["seed"] == client.settings.seed
    assert body["messages"] == [{"role": "system", "content": "system"},
                                {"role": "user", "content": "Return JSON"}]
