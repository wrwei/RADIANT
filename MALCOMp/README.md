# MALCOMp

MALCOMp is the Python multi-agent component of RADIANT. It derives
terminology, an Emfatic DSL, an executable EOL model-construction program, and
state-machine artefacts from natural-language requirements. Each stage also
produces traceability JSON.

MALCOMp uses Microsoft AutoGen for agent orchestration and supports OpenAI,
OpenAI-compatible endpoints, and Anthropic through its YAML configuration.

## Quick Start

Run these commands from `MALCOMp/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item ..\.env.example ..\.env
python .\run.py
```

Edit the repository-root `.env` before running. OpenAI-compatible providers
use `OPENAI_API_KEY`; Anthropic uses `ANTHROPIC_API_KEY`. The default AUV
configuration currently targets a DeepSeek OpenAI-compatible endpoint, so its
key is supplied through `OPENAI_API_KEY`.

## Project Structure

```text
MALCOMp/
  base.py                 Shared stage infrastructure and agent orchestration
  run.py                  Multi-agent command-line entry point
  run_single_agent.py     Single-agent evaluation baseline
  eol_execution.py        EOL execution and repair support
  phases/
    concept.py
    dsml.py
    model.py
    behaviour.py

config.yaml               Single pipeline config (models: map + stages)
case_studies/             (repo root — sibling of MALCOMp/, MALCOMj/, ...)
  auv/
    assets/               Requirement inputs, per-phase prompts, and fixtures/
    output/runs/          Archived run artefacts
```

## Pipeline Phases

The four LLM phases (RADIANT Phases 2-5) and their CLI tokens:

| CLI token | Phase | Main output |
|---|---|---|
| `concept` | Concept Extraction | `result_concept_trace.json` |
| `dsml` | DSML Creation | `result_dsml.emf`, `result_dsml_trace.json` |
| `model` | Model Creation | `result_model.eol`, `result_model_trace.json` |
| `behaviour` | Behaviour Model Creation | `result_behaviour_model.rct`, `result_behaviour_trace.json` |

Phases run in the order supplied. Running the full pipeline uses the order
shown above and archives all configured outputs under one run ID.

## Usage

```powershell
# Full pipeline with the root config.yaml (default model)
python .\run.py

# Selected phases
python .\run.py concept dsml

# Pick a model from the config's `models:` map
python .\run.py --model gpt_4o

# Repeat concept extraction for evaluation
python .\run.py concept --repeat 10

# Set an explicit archive directory name
python .\run.py --run-id experiment_001
```

The single-agent baseline has a separate CLI:

```powershell
python .\run_single_agent.py --help
```

## Configuration

Paths in the root `config.yaml` are resolved relative to it (the repo root).
The main sections are:

- `models` / `default_model`: named model variants (provider, name, endpoint,
  temperature); pick one with `--model <key>`.
- `case_study` / `prompts_dir`: the active case study (override `--case-study`)
  and the shared prompts root.
- `stages`: per-phase requirements, agents, limits, assets, and output names.

See [`config.yaml`](../config.yaml) (repo root) for the complete
format and [`SWITCHING_MODELS.md`](SWITCHING_MODELS.md) for provider examples.

## Creating a Case Study

A case study supplies only **requirements + a system description**; prompts are
shared (`prompts/`) and everything else is produced by the pipeline. Create the
directory and run with `--case-study <name>`:

```text
prompts/                           shared, generic (concept/ dsml/ model/ behaviour/)
case_studies/my_project/
  requirements/                    hand-authored requirement models
    requirement_architecture.json
    requirement_behaviour.json
  system_description/              hand-authored domain description
    system_description.txt
  output/                          generated (chained intermediates + archived runs)
```

```powershell
python .\run.py --case-study my_project
```

Then run:

```powershell
python .\run.py --config .\examples\my_project\config.yaml
```

The bundled AUV requirement files show the expected JSON structure.

## Web UI and Evaluation

- [`../MALCOM-web/`](../MALCOM-web/) runs the stage classes in-process and
  streams agent activity through a browser UI.
- [`../malcom.evaluation/metrics/`](../malcom.evaluation/metrics/)
  scores archived runs against documented references.

Python 3.10+ is required.
