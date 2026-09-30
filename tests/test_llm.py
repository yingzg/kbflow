import json

import pytest

from kbflow import llm


def test_require_llm_raises_without_key(monkeypatch):
    monkeypatch.delenv("KBFLOW_LLM_API_KEY", raising=False)
    with pytest.raises(llm.LLMNotConfiguredError):
        llm.require_llm()


def test_require_llm_raises_with_empty_key(monkeypatch):
    monkeypatch.setenv("KBFLOW_LLM_API_KEY", "")
    with pytest.raises(llm.LLMNotConfiguredError):
        llm.require_llm()


def test_require_llm_raises_with_whitespace_key(monkeypatch):
    monkeypatch.setenv("KBFLOW_LLM_API_KEY", "   ")
    with pytest.raises(llm.LLMNotConfiguredError):
        llm.require_llm()


def test_complete_posts_and_returns_content(monkeypatch):
    monkeypatch.setenv("KBFLOW_LLM_API_KEY", "test-key")
    monkeypatch.setenv("KBFLOW_LLM_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("KBFLOW_LLM_MODEL", "gpt-4o-mini")

    captured = {}

    def fake_post_json(url, headers, body):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = body
        return {"choices": [{"message": {"content": "hello from llm"}}]}

    monkeypatch.setattr(llm, "_http_post_json", fake_post_json)

    client = llm.require_llm()
    result = client.complete("hi", system="be brief")

    assert result == "hello from llm"
    assert captured["url"] == "https://example.com/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"

    body = json.loads(captured["body"].decode("utf-8"))
    assert body["model"] == "gpt-4o-mini"
    assert body["messages"] == [
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": "hi"},
    ]


def test_complete_without_system_message(monkeypatch):
    monkeypatch.setenv("KBFLOW_LLM_API_KEY", "k")
    monkeypatch.setenv("KBFLOW_LLM_MODEL", "gpt-4o-mini")

    captured = {}

    def fake_post_json(url, headers, body):
        captured["body"] = body
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(llm, "_http_post_json", fake_post_json)

    client = llm.require_llm()
    assert client.complete("hi") == "ok"

    body = json.loads(captured["body"].decode("utf-8"))
    assert body["messages"] == [{"role": "user", "content": "hi"}]


def test_http_post_401_raises_friendly_llm_error(monkeypatch):
    class FakeResponse:
        status_code = 401

        def raise_for_status(self):
            raise RuntimeError("401")

        def json(self):
            return {}

    def fake_post(url, headers=None, content=None, timeout=None):
        return FakeResponse()

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    with pytest.raises(llm.LLMError) as exc:
        llm._http_post_json("https://x/v1/chat/completions", {}, b"{}")
    assert "401" in str(exc.value)
    assert "BASE_URL" in str(exc.value)
