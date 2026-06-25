# MALCOMp User Guide

**MALCOMp** (Multi-Agent LLM Component) is the Python-based pipeline of the RADIANT project. It uses multi-agent LLM conversations (via Microsoft Autogen) to automatically extract metamodels, model instances, and state machines from natural language requirements, while generating traceability links at each step.

---

## Prerequisites

### Python

Python 3.10 or later is required.

### Dependencies

Install the required packages:

```
pip install -r requirements.txt
```

Or manually:

```
pip install pyautogen python-dotenv pyyaml
```

| Package          | Purpose                                    |
| ---------------- | ------------------------------------------ |
| `pyautogen`      | Multi-agent LLM orchestration framework    |
| `python-dotenv`  | Loads the API key from the `.env` file     |
| `pyyaml`         | Reads the `config.yaml` configuration file |

### API Key

MALCOMp requires access to an OpenAI-compatible or Anthropic API. Before running, create a `.env` file in the `MALCOMp/` directory:

```
cp .env.example .env
# Edit .env and add your key
```

The `.env` file is gitignored and should never be committed.

---

## Project Structure

```
MALCOMp/
    .env.example         Template for API keys
    .gitignore           Ignores .env, __pycache__, .cache, output/
    requirements.txt     Python dependencies
    base.py              Shared infrastructure for all stages
    run.py               Unified command-line entry point
    phases/
        __init__.py
        concept.py     Phase 2: Concept Extraction Layer
        dsml.py        Phase 3: DSML Creation Layer
        model.py       Phase 4: Model Creation Layer
        behaviour.py   Phase 5: Behaviour Model Creation Layer

config.yaml                          Single pipeline config (models: map + stages)
case_studies/                        (repo root — sibling of MALCOMp/)
    auv/                             AUV case study (default; assets + outputs)
        assets/                      Per-phase prompts, requirement inputs, fixtures/
        output/                      Generated results (created automatically)
```

---

## Configuration

The pipeline is driven by one `config.yaml` at the repository root. It holds a `models:` map (pick one with `--model <key>`, default `default_model`) and the shared `stages:` block. All paths in `config.yaml` are resolved relative to the config file's directory.

The file has three sections:

### Model settings

A `models:` map declares the LLM variants; `default_model` picks the one used
when `--model` is omitted. Select a model by key with `--model <key>` (or the
`MALCOMP_MODEL` env var).

```yaml
default_model: deepseek_v4
models:
  deepseek_v4:
    name: "deepseek-v4-pro"
    temperature: 0.0
    api_type: "openai"                          # "openai" or "anthropic"
    api_base_url: "https://api.deepseek.com"
  gpt_4o:
    name: "gpt-4o"
    temperature: 0.5
    api_type: "openai"
    api_base_url: "https://api.openai.com/v1"
```

You can override `api_base_url` at runtime via the `OPENAI_API_BASE` environment
variable. See [`SWITCHING_MODELS.md`](SWITCHING_MODELS.md) for the full reference.

### Case study + prompts

```yaml
case_study: "auv"        # selects case_studies/<case_study>/ (override: --case-study)
prompts_dir: "prompts"   # shared, generic prompts (repo-relative)
```

The active case study supplies only `requirements/` and `system_description/`;
its generated artefacts go to `case_studies/<case_study>/output/`. Prompts are
shared across all case studies under `prompts_dir`.

### Stage settings

Each pipeline phase has its own block under `stages:`. A phase block contains:

- **`requirement_file`** - Requirements JSON, relative to the case study dir (e.g. `requirements/requirement_architecture.json`).
- **`max_rounds`** - Maximum conversation rounds for the multi-agent group chat.
- **`asset_files`** - Logical name → filename. Each filename is resolved across, in order: `prompts_dir` (prompt templates / few-shot / chain-of-thought), the case study's `output/` (freshly chained prior-phase artefacts), the case study dir (e.g. `system_description/…`), then `fixtures/` (golden fallback).
- **`output`** - Defines where results are saved:
  - `json_file` / `json_tag` / `json_agent` - The traceability JSON output.
  - `code_file` / `code_agent` - The code artifact output (metamodel, EOL program, or state machine).

---

## Pipeline Phases

MALCOMp realises RADIANT **Phases 2-5** as four sequential Multi-Agent LLM
layers (`concept` -> `dsml` -> `model` -> `behaviour`). Each phase feeds its
output into the next. Every phase also runs a `Trace_Generation_Agent` that
produces the traceability JSON.

### Phase 2: Concept Extraction (`concept`)

Extracts domain **Concepts** and their **Instances** from requirements.

- **Input**: `requirement_architecture.json`
- **Agents**: `Concept_Extraction_Agent` (extracts), `Concept_Checker_Agent` (validates), `Trace_Generation_Agent` (traceability)
- **Output**: `result_concept_trace.json` - extracted concept-instance pairs with traceability back to requirement GIDs

### Phase 3: DSML Creation (`dsml`)

Generates an **Emfatic metamodel** (the domain-specific modelling language) from the requirements and the extracted concepts.

- **Input**: `requirement_architecture.json` + `result_concept_trace.json`
- **Agents**: `DSML_Extraction_Agent` (creates Emfatic), `DSML_Checker_Agent` (validates syntax), `DSML_Refactoring_Agent` (consolidates), `Trace_Generation_Agent`
- **Output**:
  - `result_dsml.emf` - the generated Emfatic metamodel
  - `result_dsml_trace.json` - traceability from requirements to metamodel elements

### Phase 4: Model Creation (`model`)

Generates an **EOL (Epsilon Object Language) program** that creates a model instance conforming to the metamodel.

- **Input**: `requirement_architecture.json` + `result_concept_trace.json` + `result_dsml.emf`
- **Agents**: `Model_Creator` (writes EOL), `Model_Checker` (validates), `Model_Refactorer` (consolidates), `Trace_Generation_Agent`
- **Output**:
  - `result_model.eol` - the generated EOL program
  - `result_model_trace.json` - traceability from requirements to model elements

### Phase 5: Behaviour Model Creation (`behaviour`, optional)

Generates a **RoboChart-like state machine** from behavioural requirements (for safety-critical systems).

- **Input**: `requirement_behaviour.json`
- **Agents**: `Behaviour_Model_Creation_Agent` (generates the state machine), `Behaviour_Checker_Agent` (validates and corrects the DSL), `Trace_Generation_Agent`
- **Output**:
  - `result_behaviour_model.rct` - the generated state machine
  - `result_behaviour_trace.json` - traceability from requirements to state-machine elements

---

## Running the Pipeline

All commands should be run from the `MALCOMp/` directory.

### Run the full pipeline

```
python run.py
```

This runs all four phases in order using the default AUV example and the
`default_model`: `concept` -> `dsml` -> `model` -> `behaviour`.

### Run specific phases

```
python run.py concept dsml
```

Only the named phases are executed, in the order given.

### Run concept extraction multiple times

For experimental evaluation, concept extraction can be repeated to collect multiple samples:

```
python run.py concept --repeat 10
```

### Pick a model

```
python run.py --model gpt_4o
```

Uses the `gpt_4o` entry from the root config's `models:` map (default: `default_model`).

### Show help

```
python run.py --help
```

---

## Input Format

Requirements are provided as JSON files. Each file must have a top-level `"requirements"` array:

```json
{
    "requirements": [
        {
            "kind": "Non-Functional Requirement",
            "name": "SD1",
            "id": "SD1",
            "description": "The AUV system is developed as a Module named \"AUV_Module\".",
            "priority": "6",
            "types": ["architecture"]
        },
        {
            "kind": "Functional Requirement",
            "name": "SD2",
            "id": "SD2",
            "description": "...",
            "priority": "5",
            "types": ["architecture"]
        }
    ]
}
```

| Field         | Description                                        |
| ------------- | -------------------------------------------------- |
| `kind`        | `"Functional Requirement"` or `"Non-Functional Requirement"` |
| `name`        | Short name identifier                              |
| `id`          | Unique GID used for traceability                   |
| `description` | The natural language requirement text               |
| `priority`    | Priority rating (string, e.g. `"1"` to `"10"`)    |
| `types`       | Array of categories, e.g. `["architecture"]`, `["performance"]` |

The pipeline uses two separate requirement files:
- **Architecture requirements** (`requirement_architecture.json`) - used by stages 1-3
- **Behavioural requirements** (`requirement_behaviour.json`) - used by stage 4

---

## Output Format

Each stage produces two types of output:

### Traceability JSON

A JSON file mapping requirement GIDs to generated artifacts. The format varies by stage:

**Term extraction** (`result_concept_trace.json`):
```json
{
    "term_trace": [
        {
            "GID": "SD1",
            "Concept": "Module",
            "Concept_description": "...",
            "Instance": "AUV_Module",
            "Instance_description": "..."
        }
    ]
}
```

**DSL extraction** (`result_dsml_trace.json`):
```json
{
    "dsl_trace": [
        {
            "requirement_gid": "SD1",
            "Emfatic_class": "Module",
            "Emfatic_attributes": ["name"],
            "Emfatic_references": ["contains"],
            "Emfatic_operations": []
        }
    ]
}
```

**Model creation** (`result_model_trace.json`):
```json
{
    "model_trace": [
        {
            "requirement_gid": "SD1",
            "Model_Element": "Module",
            "Model_Element_id": "AUV_Module",
            "Model_attribute": "name",
            "Attribute_value": "AUV_Module",
            "Model_reference": "contains",
            "Reference_value": "AUV_Platform"
        }
    ]
}
```

**State machine extraction** (`result_behaviour_trace.json`):
```json
{
    "stm_trace": [
        {
            "requirement_gid": "BR1",
            "source state": "Idle",
            "end state": "Moving",
            "transition": "start"
        }
    ]
}
```

### Code Artifacts

- `result_dsml.emf` - Emfatic metamodel (stage 2)
- `result_model.eol` - EOL model creation program (stage 3)
- `result_behaviour_model.rct` - RoboChart state machine DSL code (stage 4)

---

## Creating a New Case Study

A case study supplies only **requirements + a system description** — prompts are
shared and the pipeline produces everything else.

1. **Create the directory** with two subfolders:
   ```
   case_studies/my_project/
       requirements/         requirement_architecture.json, requirement_behaviour.json
       system_description/   system_description.txt
   ```

2. **Write your requirements** in the JSON format shown above (architecture
   requirements → Phases 2-4; behavioural requirements → Phase 5).

3. **Write a system description** in `system_description/system_description.txt` —
   it gives the LLM agents context about the domain.

4. **Run it** with `--case-study`:
   ```
   python run.py --case-study my_project
   ```
   No per-study config or prompt copies needed — `run.py` resolves
   `case_studies/my_project/`, uses the shared `prompts/`, and chains each phase's
   output into `case_studies/my_project/output/`. The web UI also lists it in the
   case-study selector automatically.

The bundled `case_studies/auv/` study serves as a complete reference for the
expected layout (requirements, system description, prompts, and outputs).

---

## Troubleshooting

| Problem | Solution |
| ------- | -------- |
| `EnvironmentError: OPENAI_API_KEY not set` | Create a `.env` file with `OPENAI_API_KEY=your-key` |
| `EnvironmentError: ANTHROPIC_API_KEY not set` | Add `ANTHROPIC_API_KEY=your-key` to `.env` |
| `ModuleNotFoundError: No module named 'autogen'` | Run `pip install pyautogen` |
| `ModuleNotFoundError: No module named 'dotenv'` | Run `pip install python-dotenv` |
| `ModuleNotFoundError: No module named 'yaml'` | Run `pip install pyyaml` |
| `FileNotFoundError` on an asset file | Check that the filename in `config.yaml` matches the actual file in `assets/` |
| Phase 3 or 4 fails to find `result_concept_trace.json` | The `concept` phase must run first. Run the full pipeline or run `python run.py concept` first |
| API timeout or rate limit errors | Check your API key, increase the `timeout` if needed, or reduce `max_rounds` in `config.yaml` |
