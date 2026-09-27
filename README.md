# RADIANT

**RADIANT**: Requirement-driven, Agent-Directed generatIon of trAceable, heterogeNeous sysTem models.

RADIANT is a research prototype for deriving Model-Driven Engineering (MDE)
artefacts from natural-language requirements. It combines a multi-agent LLM
pipeline, deterministic EMF/Epsilon tooling, a browser interface, traceability
artefacts, and stage-specific evaluation metrics.

## Repository Layout

| Directory | Purpose |
|---|---|
| [`MALCOMp/`](MALCOMp/) | Python multi-agent pipeline for term, DSL, model, and state-machine extraction |
| [`MALCOMj/`](MALCOMj/) | Java/Gradle EMF and Epsilon transformations, validation tasks, and evaluation helpers |
| [`MALCOM-web/`](MALCOM-web/) | FastAPI and WebSocket UI for running MALCOMp and MALCOMj interactively |
| [`case_studies/`](case_studies/) | Case-study inputs, per-phase prompts, and run outputs (the single root `config.yaml` drives them; AUV is the default and reference study) |
| [`malcom.evaluation/`](malcom.evaluation/) | Auditable reference artefacts, metric implementations, and generated reports |
| [`malcom.requirement/`](malcom.requirement/) | Requirement & terminology EMF metamodels, edit/editor, and Sirius modelling tooling (the `malcom.requirement.*` plug-ins) |
| [`malcom.bifrost/`](malcom.bifrost/) | Bifrost traceability EMF metamodel, edit/editor, and Sirius model-management tooling (the `malcom.bifrost.*` plug-ins) |
| [`archive/`](archive/) | Historical AUV case-study workspace retained for reference |

The Eclipse plug-ins are optional for the standalone Gradle, Python, and web
workflows.

## Pipeline

MALCOMp runs four stages in sequence:

1. **Term extraction**: requirements to concepts, instances, and trace links.
2. **DSL extraction**: requirements and terms to an Emfatic metamodel.
3. **Model creation**: requirements and the generated metamodel to an EOL
   program and executed EMF model.
4. **State-machine extraction**: behavioural requirements and architecture
   context to RoboChart-like state-machine text.

Generated artefacts are archived under
`case_studies/auv/output/runs/<run-id>/`.

## Requirements

- Python 3.10+
- Java 17+
- Gradle 8+
- An API key for OpenAI, an OpenAI-compatible provider, or Anthropic

## Quick Start

### 1. Configure the Python environment

PowerShell:

```powershell
cd MALCOMp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item ..\.env.example ..\.env
```

Edit the repository-root `.env`. For OpenAI-compatible endpoints, including
the default DeepSeek configuration, set the provider key as
`OPENAI_API_KEY`. The endpoint can be set in the YAML config or overridden by
`OPENAI_API_BASE`.

### 2. Run MALCOMp

Run all four stages (Phases 2–5) with the bundled AUV case study:

```powershell
cd MALCOMp
python .\run.py
```

Run selected stages, pick a model, or repeat extraction:

```powershell
python .\run.py concept dsml
python .\run.py behaviour --model deepseek_v3
python .\run.py concept --repeat 10
```

Valid stage names are `concept`, `dsml`, `model`, and `behaviour`.

**Running the pipeline from the CLI (no web UI):** see the operator runbook in
[`docs/pipeline/`](docs/pipeline/README.md) — setup, commands, configuration,
outputs/verification, and troubleshooting. It is written so Claude Code can run the
pipeline end-to-end from the terminal.

### 3. Run MALCOMj

```powershell
cd MALCOMj
gradle runAuvValidation
gradle runRequirementGen
gradle runAll
```

See [`MALCOMj/README.md`](MALCOMj/README.md) for the complete task list.

### 4. Start the web UI

```powershell
cd MALCOM-web
python -m pip install -r requirements.txt
python -m web
```

Open <http://localhost:8000>. The standard sibling layout is detected
automatically; `MALCOMP_DIR` and `MALCOMJ_DIR` can override it.

## Evaluation

The current evaluation framework is under
[`malcom.evaluation/metrics/`](malcom.evaluation/metrics/).
It provides deterministic precision, recall, and F1 metrics for:

| Stage | Primary metric |
|---|---|
| Term extraction | `dedup_vocabulary_f1` |
| Emfatic generation | `end_to_end_weighted_f1` plus official parser validity |
| Model creation | `end_to_end_micro_f1` over executed EMF facts |
| State-machine extraction | `behavior_micro_f1` |

The audited AUV expert reference is documented in
[`malcom.evaluation/reference_models/auv_independent_expert_20260612/`](malcom.evaluation/reference_models/auv_independent_expert_20260612/).
Metric reports are generated under
`malcom.evaluation/metrics/results/`.

Example:

```powershell
cd malcom.evaluation\metrics\term_extraction
python .\compute.py
```

See the [metrics README](malcom.evaluation/metrics/README.md) for
metric definitions, reference sources, and per-stage commands.

## Metamodel Architecture

The reusable Eclipse projects define four core metamodels:

| Metamodel | Namespace URI | Purpose |
|---|---|---|
| `base.ecore` | `http://www.sawg.org/base` | Shared element and description types |
| `requirement.ecore` | `http://www.sawg.org/requirement` | Functional and non-functional requirements |
| `terminology.ecore` | `http://www.sawg.org/terminology` | Concepts, instances, and terminology packages |
| `bifrost.ecore` | `http://www.sawg.org/bifrost` | Cross-artefact traceability links |

## Security and Generated Files

- Keep API keys only in `.env`; the file is ignored by Git.
- Pipeline outputs and evaluation reports can be large. Review staged files
  before committing generated run directories.
- The `archive/` tree is historical and is not the active implementation.
