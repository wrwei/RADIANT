# Switching LLM Models in MALCOMp

The pipeline is driven by a single root `config.yaml` (at the repository root)
that holds a **`models:` map** — a named entry per LLM variant — plus a
`default_model`. You switch models by **name**, without editing the config:

```bash
cd MALCOMp
python run.py                       # uses default_model
python run.py --model gpt_4o        # uses the `gpt_4o` entry from models:
MALCOMP_MODEL=gpt_4o python run.py  # same, via env var
```

`run_single_agent.py` takes the same `--model <key>`, and `run_evaluation.py`
sweeps every key in the map by default. Provider secrets always come from `.env`.

---

## The `models:` map

```yaml
default_model: deepseek_v4

models:
  deepseek_v4:
    name: "deepseek-v4-pro"
    temperature: 0.0
    api_type: "openai"
    api_base_url: "https://api.deepseek.com"
  gpt_4o:
    name: "gpt-4o"
    temperature: 0.5
    api_type: "openai"
    api_base_url: "https://api.openai.com/v1"
  # ... more entries ...
```

Each entry is keyed by a short slug (`gpt_4o`, `deepseek_v3`, ...) that you pass
to `--model`. To **add** a model, add an entry and set the matching API key in
`.env` — nothing else changes.

| Provider | `api_type` | `.env` variable | Install command |
| -------- | ---------- | --------------- | --------------- |
| OpenAI / OpenAI-compatible | `"openai"` | `OPENAI_API_KEY` | `pip install pyautogen` |
| Anthropic | `"anthropic"` | `ANTHROPIC_API_KEY` | `pip install pyautogen[anthropic]` |

---

## Per-model fields

| Field | Required | Default | Description |
| ----- | -------- | ------- | ----------- |
| `name` | Yes | - | Model identifier string (e.g. `"gpt-4o"`, `"claude-sonnet-4-5-20250929"`) |
| `temperature` | No | `0.5` | Sampling temperature. Lower (0.2) = more deterministic; higher (0.8) = more varied |
| `api_type` | No | `"openai"` | Provider: `"openai"` or `"anthropic"` |
| `api_base_url` | No | `""` | Base URL for OpenAI-compatible endpoints. Ignored when `api_type` is `"anthropic"` |

The `OPENAI_API_BASE` environment variable, if set, overrides `api_base_url` at
runtime — handy for redirecting an `openai` entry to a proxy / self-hosted /
OpenRouter / vLLM endpoint without editing the config.

---

## OpenAI-compatible entries

```yaml
models:
  gpt_4o:        { name: "gpt-4o",        temperature: 0.5, api_type: "openai", api_base_url: "https://api.openai.com/v1" }
  gpt_4o_mini:   { name: "gpt-4o-mini",   temperature: 0.5, api_type: "openai", api_base_url: "https://api.openai.com/v1" }
  qwen3_32b:     { name: "Qwen/Qwen3-32B", temperature: 0.5, api_type: "openai", api_base_url: "https://openrouter.ai/api/v1" }
```

```
# .env
OPENAI_API_KEY=sk-your-openai-key-here
# optional: redirect openai-type entries to another OpenAI-compatible endpoint
# OPENAI_API_BASE=https://openrouter.ai/api/v1
```

## Anthropic (Claude) entries

Requires `pip install pyautogen[anthropic]`. `api_base_url` is not needed.

```yaml
models:
  claude_sonnet: { name: "claude-sonnet-4-5-20250929", temperature: 0.5, api_type: "anthropic" }
  claude_opus:   { name: "claude-opus-4-6",            temperature: 0.3, api_type: "anthropic" }
  claude_haiku:  { name: "claude-haiku-4-5-20251001",  temperature: 0.5, api_type: "anthropic" }
```

```
# .env
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
```

You can keep both `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` in `.env` at once;
each run uses only the key matching the selected model's `api_type`.

---

## Troubleshooting

| Problem | Solution |
| ------- | -------- |
| `unknown model 'X'; available: [...]` | The `--model` key isn't in the `models:` map — use one of the listed keys |
| `config defines 'models' but no 'default_model'` | Add a `default_model:` (or always pass `--model`) |
| `EnvironmentError: OPENAI_API_KEY not set` | The selected model is `api_type: openai` but `OPENAI_API_KEY` is missing from `.env` |
| `EnvironmentError: ANTHROPIC_API_KEY not set` | The selected model is `api_type: anthropic` but `ANTHROPIC_API_KEY` is missing |
| `ModuleNotFoundError: No module named 'anthropic'` | Run `pip install pyautogen[anthropic]` |
| `AuthenticationError` / `401` | API key invalid or expired — regenerate it from the provider dashboard |
| `InvalidRequestError` on model name | The `name` value is wrong — check the provider's model IDs |
| Unexpected output quality | Adjust `temperature` (0.2-0.3 gives more consistent code generation) |
