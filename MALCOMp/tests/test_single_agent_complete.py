"""Tests for the single-agent _complete dispatch (provider + temperature + usage)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # MALCOMp
import run_single_agent as sa


class _Usage:
    def __init__(self, a, b, anthropic=False):
        if anthropic:
            self.input_tokens, self.output_tokens = a, b
        else:
            self.prompt_tokens, self.completion_tokens = a, b


# --- fake OpenAI client -----------------------------------------------------
class _Choice:
    def __init__(self, content):
        self.message = type("M", (), {"content": content})()


class _Completion:
    def __init__(self, content):
        self.choices = [_Choice(content)]
        self.usage = _Usage(11, 22)


class _FakeOpenAI:
    def __init__(self):
        self.calls = []

    @property
    def chat(self):
        return self

    @property
    def completions(self):
        return self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _Completion("openai-out")


# --- fake Anthropic client --------------------------------------------------
class _Block:
    def __init__(self, text):
        self.text = text
        self.type = "text"


class _Message:
    def __init__(self, text):
        self.content = [_Block(text)]
        self.usage = _Usage(7, 13, anthropic=True)


class _FakeAnthropic:
    def __init__(self):
        self.calls = []

    @property
    def messages(self):
        return self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _Message("claude-out")


def test_strip_fences():
    assert sa._strip_fences('```json\n{"a":1}\n```') == '{"a":1}'
    assert sa._strip_fences('```\nhello\n```') == 'hello'
    assert sa._strip_fences('{"a":1}') == '{"a":1}'        # no fence -> unchanged
    assert sa._strip_fences('  plain  ') == 'plain'
    assert sa._strip_fences('```emfatic\nclass A {}\n```') == 'class A {}'


def test_openai_includes_temperature_and_usage():
    client = _FakeOpenAI()
    cfg = {"model": {"name": "gpt-4o", "temperature": 0.5, "api_type": "openai"}}
    text, usage = sa._complete(client, cfg, "sys", "user")
    assert text == "openai-out"
    assert usage == (11, 22)               # (prompt, completion)
    assert client.calls[0]["temperature"] == 0.5


def test_openai_omits_temperature_when_unsupported():
    client = _FakeOpenAI()
    cfg = {"model": {"name": "gpt-5", "api_type": "openai", "supports_temperature": False}}
    sa._complete(client, cfg, "sys", "user")
    assert "temperature" not in client.calls[0]


def test_anthropic_messages_api_and_usage():
    client = _FakeAnthropic()
    cfg = {"model": {"name": "claude-opus-4-8", "api_type": "anthropic",
                     "supports_temperature": False}}
    text, usage = sa._complete(client, cfg, "sys-msg", "user-msg")
    assert text == "claude-out"
    assert usage == (7, 13)                # (input, output)
    call = client.calls[0]
    assert call["system"] == "sys-msg"
    assert "max_tokens" in call
    assert "temperature" not in call       # Opus deprecates it
