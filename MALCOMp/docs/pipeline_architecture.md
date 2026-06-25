# MALCOMp Pipeline Architecture

## Table of Contents

- [1. Overview](#1-overview)
- [2. End-to-End Pipeline Flow](#2-end-to-end-pipeline-flow)
- [3. Entry Point and CLI](#3-entry-point-and-cli)
- [4. Base Infrastructure](#4-base-infrastructure)
- [5. Phase 2: Concept Extraction](#5-phase-2-concept-extraction)
- [6. Phase 3: DSML Creation](#6-phase-3-dsml-creation)
- [7. Phase 4: Model Creation](#7-phase-4-model-creation)
- [8. Phase 5: Behaviour Model Creation](#8-phase-5-behaviour-model-creation)
- [9. Configuration Reference](#9-configuration-reference)

---

## 1. Overview

MALCOMp (Multi-Agent LLM pipeline for Model-Driven Engineering) is a multi-phase pipeline that transforms natural language requirements into formal models using multi-agent LLM conversations orchestrated by Microsoft AutoGen.

### High-Level Architecture

```
                          MALCOMp Pipeline
 ┌─────────────────────────────────────────────────────────┐
 │                                                         │
 │  requirement_architecture.json                          │
 │         │                                               │
 │         ▼                                               │
 │  ┌──────────────────┐                                   │
 │  │  Concept Extraction  │  Agents: Concept_Extraction_Agent,         │
 │  │   (max 100 rds)   │          Concept_Checker_Agent            │
 │  └────────┬─────────┘                                   │
 │           │ result_concept_trace.json                  │
 │           ▼                                              │
 │  ┌──────────────────┐                                   │
 │  │  DSML Creation   │  Agents: DSML_Extraction_Agent,          │
 │  │   (max 500 rds)   │          DSML_Checker_Agent,            │
 │  └────────┬─────────┘          DSML_Refactoring_Agent,            │
 │           │                     Trace_Generation_Agent           │
 │           │ result_dsml.emf                               │
 │           │ result_dsml_trace.json                   │
 │           ▼                                              │
 │  ┌──────────────────────┐                               │
 │  │  Model Creation   │  Agents: Model_Creator,      │
 │  │    (max 1000 rds)     │          Model_Checker,       │
 │  └────────┬─────────────┘          Model_Refactorer,    │
 │           │                         Trace_Generation_Agent       │
 │           │ result_model.eol                       │
 │           │ result_model_trace.json                   │
 │           ▼                                              │
 │       [DONE]                                             │
 │                                                         │
 │  requirement_behaviour.json                             │
 │         │                                               │
 │         ▼                                               │
 │  ┌────────────────────────────┐                         │
 │  │  Behaviour Model Creation   │  Agents: Behaviour_Model_Creation_Agent,     │
 │  │      (max 500 rds)          │          Trace_Generation_Agent │
 │  └────────┬───────────────────┘                         │
 │           │ result_behaviour_model.rct                                      │
 │           │ result_behaviour_trace.json           │
 │           ▼                                              │
 │       [DONE]                                             │
 └─────────────────────────────────────────────────────────┘
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `pyautogen>=0.2` | Microsoft AutoGen framework for multi-agent LLM conversations |
| `python-dotenv>=1.0` | Loads environment variables from `.env` files |
| `pyyaml>=6.0` | YAML parsing for `config.yaml` |

---

## 2. End-to-End Pipeline Flow

### Data Flow Between Phases

```
requirement_architecture.json ──┐
                                ▼
                    ┌───────────────────────┐
                    │   Phase 2: Concept       │
                    │   Extraction          │
                    └───────────┬───────────┘
                                │
                    result_concept_trace.json
                                │
               ┌────────────────┼────────────────┐
               ▼                ▼                 │
   ┌───────────────────┐  requirement_            │
   │  Phase 3: DSML     │  architecture.json       │
   │  Extraction       │                          │
   └─────────┬─────────┘                          │
             │                                     │
    result_dsml.emf                                 │
    result_dsml_trace.json                     │
             │                                     │
             ▼                                     ▼
   ┌───────────────────────┐        requirement_architecture.json
   │  Phase 4: Model   │        result_concept_trace.json
   │  Creation             │        result_dsml.emf
   └─────────┬─────────────┘
             │
    result_model.eol
    result_model_trace.json


requirement_behaviour.json ──┐
                             ▼
                 ┌──────────────────────────┐
                 │  Phase 5: Behaviour  │
                 │  Extraction              │
                 └────────────┬─────────────┘
                              │
                     result_behaviour_model.rct
                     result_behaviour_trace.json
```

**Key observations:**
- Phases 2-4 form a sequential chain, each consuming outputs from prior phases.
- Phase 5 is independent; it uses a separate input file (`requirement_behaviour.json`) and has no dependency on Phases 2-4.
- Every phase produces a **traceability JSON** linking requirements (by GID) to generated artefacts.
- Phases 3, 4, and 5 also produce a **code artefact** (Emfatic metamodel / EOL program / RoboChart state machine).

### Execution Sequence

1. **Initialisation**: Load config, validate API keys, resolve paths.
2. **For each phase** (in order: concept, dsml, model, behaviour):
   - Instantiate the stage class.
   - Load requirement JSON file.
   - Create `RequirementFeederAgent` + stage-specific agents.
   - Create `GroupChat` with round-robin speaker selection.
   - Call `initiate_chat()` — requirements are fed one-by-one.
   - Extract and store JSON traceability output.
   - Extract and store code artefact (if applicable).
3. **Completion**: Log phase completion, move to next phase.

---

## 3. Entry Point and CLI

**Location:** `run.py`

### Usage

```bash
# Run all stages (default)
python run.py

# Run specific stages
python run.py concept dsml

# Custom config file
python run.py --config path/to/config.yaml

# Repeat concept extraction N times (evaluation mode)
python run.py concept --repeat 10
```

### Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `stages` | positional | all four | Phases to run: `concept`, `dsml`, `model`, `behaviour` |
| `--config` | string | `../config.yaml` | Path to the root config YAML |
| `--repeat` | int | 1 | Run concept extraction N times (only applies to `concept`) |

### Stage Registry

```python
STAGES = {
    "concept":   ConceptExtraction,
    "dsml":      DSMLCreation,
    "model":     EMFModelCreation,
    "behaviour": BehaviourModelCreation,
}
```

---

## 4. Base Infrastructure

**Location:** `base.py`

### `Base` Class

The abstract base class shared by all four stages. Handles configuration loading, agent creation, group chat orchestration, and output storage.

#### Initialisation Flow

1. Load `.env` file (API keys).
2. Parse `config.yaml` and resolve paths relative to the config file directory.
3. Validate that the correct API key is set (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`).
4. Build LLM `config_list` for AutoGen agents.
5. Create `RequirementFeederAgent` as the "user" agent.
6. Initialise empty `agents` list for subclasses to populate.

#### LLM Configuration

All agents share the same default LLM config:

```python
{
    "temperature": 0.5,       # From config.yaml model.temperature
    "config_list": [{         # Built from .env + config.yaml
        "model": "gpt-4o",
        "api_key": "sk-...",
        "api_type": "openai"  # or "anthropic"
    }],
    "timeout": 600000,        # 10 minutes
    "cache_seed": None,       # No caching
}
```

Supports both OpenAI and Anthropic providers via `model.api_type` in config.

#### Agent Creation

```python
def create_agent(self, name, system_message, description, **agent_kwargs):
```

Creates a `ConversableAgent` with the default LLM config and registers it in `self.agents`.

#### Group Chat Setup

```python
def init_group_chat(self):
```

Creates an `autogen.GroupChat` with:
- All agents (user + processing agents)
- `speaker_selection_method="round_robin"`
- `max_round` from stage config (default 100)
- `send_introductions=True`

#### Pipeline Execution

```python
def run(self, message=""):
```

1. Calls `self.user.initiate_chat(self.group_chat_manager)`.
2. Extracts JSON traceability from the designated `json_agent`.
3. Extracts code artefact from the designated `code_agent` (if configured).
4. Stores both to `output_dir`.

#### Output Storage

- **`store_json()`**: Collects all messages from `json_agent`, parses JSON, aggregates into a list under a root key (`json_tag`), writes to file.
- **`_store_last_agent_output()`**: Takes the last message from `code_agent` and writes it verbatim to file.

### `RequirementFeederAgent` Class

A specialised `ConversableAgent` that replaces human input with sequential requirement feeding.

```python
class RequirementFeederAgent(ConversableAgent):
    """A ConversableAgent that feeds requirements from a JSON file one by one."""

    def __init__(self, file_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_path = file_path
        self.current_index = 0
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)["requirements"]

    def get_human_input(self, prompt):
        if self.current_index < len(self.data):
            item = self.data[self.current_index]
            reply = json.dumps(item)
            self.current_index += 1
        else:
            reply = "exit"
        self._human_input.append(reply)
        return reply
```

Maintains a `current_index` pointer. Each call to `get_human_input()` returns one requirement as JSON and advances the pointer. When all requirements are consumed, returns `"exit"` to terminate the conversation.

---

## 5. Phase 2: Concept Extraction

**Location:** `phases/concept.py`

**Purpose:** Extract domain concepts and their instances from natural language requirements.

### Agents

| Agent | Role | Description |
|-------|------|-------------|
| **Concept_Extraction_Agent** | Generator | Analyses each requirement to identify Concepts (classes) and Instances (named objects). Guided by chain-of-thought prompts and few-shot examples. |
| **Concept_Checker_Agent** | Validator | Reviews the extraction for correctness: singular noun concepts, quoted instances, no duplicates, proper JSON format. Outputs corrected JSON if needed. |

### Multi-Agent Conversation Pattern

```
RequirementFeederAgent ──► Concept_Extraction_Agent ──► Concept_Checker_Agent
        │                                          │
        │◄─────────── (next requirement) ◄─────────┘
```

Per requirement:
1. **RequirementFeederAgent** provides one requirement JSON.
2. **Concept_Extraction_Agent** extracts concepts and instances into JSON.
3. **Concept_Checker_Agent** validates and corrects the extraction.
4. Cycle repeats for the next requirement.

### Asset Files

| Config Key | File | Purpose |
|-----------|------|---------|
| `system_description` | `system_description.txt` | Description of the system being modelled |
| `few_shot_example` | `concept/few_shot_example.txt` | Example requirement-to-concept extractions |
| `chain_of_thought_extraction` | `concept/chain_of_thought_extraction.txt` | Step-by-step reasoning guide for extraction |
| `chain_of_thought_checker` | `concept/chain_of_thought_checker.txt` | Correctness criteria for validation |

### Output

**Traceability JSON** (`result_concept_trace.json`):
```json
{
    "req": [
        {
            "Requirement": "The AUV system is developed as a Module named \"AUV_Module\".",
            "GID": "SD1",
            "Concept": "Module",
            "Concept_description": null,
            "Instance": "AUV_Module",
            "Instance_of": "Module",
            "Instance_description": null,
            "Requirement_kind": "Non-Functional",
            "Non-Requirement_type": "architecture"
        }
    ]
}
```

### Repeat Mode

The `--repeat N` CLI flag creates N independent runs of this stage, each producing a dated output file for evaluation purposes:

```
2026-02-19result_concept_extractor_1.json
2026-02-19result_concept_extractor_2.json
...
```

---

## 6. Phase 3: DSML Creation

**Location:** `phases/dsml.py`

**Purpose:** Generate an Emfatic metamodel (EMF Domain Specific Language) from requirements and previously extracted terms.

### Agents

| Agent | Role | Description |
|-------|------|-------------|
| **DSML_Extraction_Agent** | Generator | Creates Emfatic metamodel code from requirements, guided by concept extraction results, chain-of-thought, and few-shot examples. |
| **DSML_Checker_Agent** | Validator | Validates Emfatic syntax, tree structure, unique class names, proper inheritance. Uses the Emfatic language reference. |
| **DSML_Refactoring_Agent** | Refactorer | Organises and consolidates the Emfatic code. Handles containment (`val`) vs. non-containment (`ref`) references. Merges with previous answers across rounds. |
| **Trace_Generation_Agent** | Tracer | Generates traceability JSON mapping requirements (by GID) to Emfatic classes, attributes, references, and operations. |

### Multi-Agent Conversation Pattern

```
RequirementFeederAgent ──► DSML_Extraction_Agent ──► DSML_Checker_Agent ──► DSML_Refactoring_Agent ──► Trace_Generation_Agent
        │                                                                          │
        │◄──────────────────── (next requirement) ◄────────────────────────────────┘
```

### Asset Files

| Config Key | File | Purpose |
|-----------|------|---------|
| `system_description` | `system_description.txt` | System description |
| `few_shot_dsl_extraction` | `dsml/few_shot_extraction.txt` | Example metamodel extractions |
| `few_shot_dsl_checker` | `dsml/few_shot_checker.txt` | Example correct metamodels |
| `chain_of_thought_extraction` | `dsml/chain_of_thought_extraction.txt` | Reasoning guide for metamodel creation |
| `chain_of_thought_checker` | `dsml/chain_of_thought_checker.txt` | Validation criteria |
| `extracted_terms` | `result_concept_trace.json` | Output from Phase 2 |
| `emfatic_rules` | `emfatic.txt` | Emfatic language syntax reference |

### Output

**Code artefact** (`result_dsml.emf`):
```emfatic
package AUV;

abstract class NamedElement {
    attr String name;
}

class Module extends NamedElement {
    val RoboticPlatform[*] platforms;
    val Interface[*] interfaces;
    val Controller[*] controllers;
}

class RoboticPlatform extends NamedElement {
    ref Interface[*] interfaces;
}
...
```

**Traceability JSON** (`result_dsml_trace.json`):
```json
{
    "dsl_trace": [
        {
            "requirement_gid": "SD1",
            "Emfatic_class": "Module",
            "Emfatic_attributes": null,
            "Emfatic_references": ["platforms", "interfaces"],
            "Emfatic_operations": null
        }
    ]
}
```

---

## 7. Phase 4: Model Creation

**Location:** `phases/model.py`

**Purpose:** Generate an Epsilon Object Language (EOL) program that creates model instances conforming to the metamodel from Phase 3.

### Agents

| Agent | Role | Description |
|-------|------|-------------|
| **Model_Creator** | Generator | Writes EOL code to instantiate classes from the Emfatic metamodel, set attributes, and create references. Uses concept extraction + metamodel as context. |
| **Model_Checker** | Validator | Validates EOL syntax, ensures conformance to the metamodel, prevents out-of-scope creations. |
| **Model_Refactorer** | Refactorer | Consolidates EOL code from previous rounds. Merges with earlier answers into one complete program. |
| **Trace_Generation_Agent** | Tracer | Maps requirements (by GID) to created model elements, attributes, and references. |

### Multi-Agent Conversation Pattern

```
RequirementFeederAgent ──► Model_Creator ──► Model_Checker ──► Model_Refactorer ──► Trace_Generation_Agent
        │                                                                                │
        │◄──────────────────────── (next requirement) ◄──────────────────────────────────┘
```

### Asset Files

| Config Key | File | Purpose |
|-----------|------|---------|
| `system_description` | `system_description.txt` | System description |
| `few_shot_model_creation` | `model/few_shot_creation.txt` | Example EOL programs |
| `few_shot_model_checker` | `model/few_shot_checker.txt` | Example correct EOL code |
| `chain_of_thought_creation` | `model/chain_of_thought_creation.txt` | Reasoning guide for model creation |
| `chain_of_thought_checker` | `model/chain_of_thought_checker.txt` | Validation criteria |
| `chain_of_thought_trace` | `model/chain_of_thought_trace.txt` | Guidance for traceability generation |
| `extracted_terms` | `result_concept_trace.json` | Output from Phase 2 |
| `dsl_source` | `result_dsml.emf` | Output from Phase 3 |

### Output

**Code artefact** (`result_model.eol`):
```eol
var auv_module = new M!Module;
auv_module.name = "AUV_Module";

var auv_platform = new M!RoboticPlatform;
auv_platform.name = "AUV_Platform";

var sensors = new M!Interface;
sensors.name = "Sensors";

auv_platform.interfaces.add(sensors);
auv_module.platforms.add(auv_platform);
...
```

**Traceability JSON** (`result_model_trace.json`):
```json
{
    "model_trace": [
        {
            "requirement_gid": "SD1",
            "Model_Element": "Module",
            "Model_Element_id": "AUV_Module",
            "Model_attribute": "name",
            "Attribute_value": "AUV_Module",
            "Model_reference": "platforms",
            "Reference_value": "AUV_Platform"
        }
    ]
}
```

---

## 8. Phase 5: Behaviour Model Creation

**Location:** `phases/behaviour.py`

**Purpose:** Generate RoboChart state machines from behavioural requirements. This phase is independent of Phases 2-4 and uses a different input file.

### Agents

| Agent | Role | Description |
|-------|------|-------------|
| **Behaviour_Model_Creation_Agent** | Generator | Creates RoboChart DSL state machine code from behavioural requirements. Uses the RoboChart Ecore metamodel, Xtext grammar, code examples, and semantic examples as context. Has `max_consecutive_auto_reply=1`. |
| **Trace_Generation_Agent** | Tracer | Maps requirements (by GID) to states, transitions, source/end states. Has `max_consecutive_auto_reply=1`. |

### Multi-Agent Conversation Pattern

```
RequirementFeederAgent ──► Behaviour_Model_Creation_Agent ──► Trace_Generation_Agent
        │                                     │
        │◄───── (next requirement) ◄──────────┘
```

### Asset Files

| Config Key | File | Purpose |
|-----------|------|---------|
| `robochart_ecore` | `behaviour/RoboChart_ecore.txt` | RoboChart metamodel in Emfatic |
| `xtext` | `Xtext.txt` | Xtext grammar for RoboChart DSL |
| `code_snippet_1` | `code_snippet_1.txt` | First RoboChart code example |
| `code_snippet_2` | `code_snippet_2.txt` | Second RoboChart code example |
| `semantic` | `semantic.txt` | Semantic examples for entry/exit actions and event transitions |

### Output

**Code artefact** (`result_behaviour_model.rct`):
```robochart
stm LRE_Beh {
    requires Inputs
    requires Outputs
    initial i0

    state OCM {
        entry advVel ! vel
    }
    state MOM {
        entry advVel ! 1
    }

    transition t0 {
        from i0
        to OCM
    }
    transition t1 {
        from OCM
        to MOM
        trigger reqVel ? x
        condition x > threshold
        action advVel ! x
    }

    var cobs : Close
    var vel : real
    event reqVel
    event advVel
}
```

**Traceability JSON** (`result_behaviour_trace.json`):
```json
{
    "stm_trace": [
        {
            "requirement_gid": "LRE-NF1",
            "source state": "i0",
            "end state": "OCM",
            "transition": "t0"
        }
    ]
}
```

---

## 9. Configuration Reference

**Location:** `config.yaml` (repository root)

### Full Structure

```yaml
default_model: deepseek_v4                   # active model when --model is omitted
models:                                      # named LLM variants; pick with --model <key>
  deepseek_v4:
    name: "deepseek-v4-pro"
    temperature: 0.0
    api_type: "openai"                       # "openai" or "anthropic"
    api_base_url: "https://api.deepseek.com"
  gpt_4o:
    name: "gpt-4o"
    temperature: 0.5
    api_type: "openai"
    api_base_url: "https://api.openai.com/v1"

case_study: "auv"          # selects case_studies/<case_study>/ (override: --case-study)
prompts_dir: "prompts"     # shared, generic prompts root

stages:
  concept_extraction:
    requirement_file: "requirements/requirement_architecture.json"
    max_rounds: 100
    asset_files:
      system_description: "system_description/system_description.txt"
      few_shot_example: "concept/few_shot_example.txt"
      chain_of_thought_extraction: "concept/chain_of_thought_extraction.txt"
      chain_of_thought_checker: "concept/chain_of_thought_checker.txt"
    output:
      json_file: "result_concept_trace.json"
      json_tag: "term_trace"
      json_agent: "Trace_Generation_Agent"

  dsml_creation:
    requirement_file: "requirements/requirement_architecture.json"
    max_rounds: 500
    asset_files:
      system_description: "system_description/system_description.txt"
      few_shot_dsl_extraction: "dsml/few_shot_extraction.txt"
      few_shot_dsl_checker: "dsml/few_shot_checker.txt"
      chain_of_thought_extraction: "dsml/chain_of_thought_extraction.txt"
      chain_of_thought_checker: "dsml/chain_of_thought_checker.txt"
      extracted_terms: "result_concept_trace.json"
      emfatic_rules: "dsml/emfatic.txt"
    output:
      json_file: "result_dsml_trace.json"
      json_tag: "dsl_trace"
      json_agent: "Trace_Generation_Agent"
      code_file: "result_dsml.emf"
      code_agent: "DSML_Refactoring_Agent"

  emf_model_creation:
    requirement_file: "requirements/requirement_architecture.json"
    max_rounds: 1000
    asset_files:
      system_description: "system_description/system_description.txt"
      few_shot_model_creation: "model/few_shot_creation.txt"
      few_shot_model_checker: "model/few_shot_checker.txt"
      chain_of_thought_creation: "model/chain_of_thought_creation.txt"
      chain_of_thought_checker: "model/chain_of_thought_checker.txt"
      chain_of_thought_trace: "model/chain_of_thought_trace.txt"
      extracted_terms: "result_concept_trace.json"
      dsl_source: "result_dsml.emf"
    output:
      json_file: "result_model_trace.json"
      json_tag: "model_trace"
      json_agent: "Trace_Generation_Agent"
      code_file: "result_model.eol"
      code_agent: "Model_Refactorer"

  behaviour_model_creation:
    requirement_file: "requirements/requirement_behaviour.json"
    max_rounds: 500
    asset_files:
      robochart_ecore: "behaviour/RoboChart_ecore.txt"
      xtext: "behaviour/Xtext.txt"
      code_snippet_1: "behaviour/code_snippet_1.txt"
      code_snippet_2: "behaviour/code_snippet_2.txt"
      semantic: "behaviour/semantic.txt"
    output:
      json_file: "result_behaviour_trace.json"
      json_tag: "stm_trace"
      json_agent: "Trace_Generation_Agent"
      code_file: "result_behaviour_model.rct"
      code_agent: "Behaviour_Model_Creation_Agent"
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `models.<key>.name` | string | Yes | LLM model identifier (e.g., `gpt-4o`, `claude-sonnet-4-5-20250929`) |
| `models.<key>.temperature` | float | No | Sampling temperature 0.0-1.0 (default: 0.5) |
| `models.<key>.api_type` | string | No | `"openai"` (default) or `"anthropic"` |
| `models.<key>.api_base_url` | string | No | Base URL for OpenAI-compatible endpoints |
| `default_model` | string | Yes | Model key used when `--model` is omitted |
| `case_study` | string | Yes | Active case study under `case_studies/` (override: `--case-study`) |
| `prompts_dir` | string | No | Shared prompts root, relative to config file (default: `"prompts"`) |
| `stages.<name>.requirement_file` | string | Yes | Requirements JSON, relative to the case study dir |
| `stages.<name>.max_rounds` | int | No | Max group chat rounds (default: 100) |
| `stages.<name>.asset_files.<key>` | string | Yes | Filename resolved across prompts_dir, output/, case dir, fixtures/ |
| `stages.<name>.output.json_file` | string | Yes | Output JSON traceability filename |
| `stages.<name>.output.json_tag` | string | Yes | Root key in the output JSON |
| `stages.<name>.output.json_agent` | string | Yes | Agent whose messages contain the JSON output |
| `stages.<name>.output.code_file` | string | No | Code artefact output filename |
| `stages.<name>.output.code_agent` | string | No | Agent whose last message is the code artefact |

### Environment Variables

| Variable | Required When | Description |
|----------|-------------|-------------|
| `OPENAI_API_KEY` | `api_type = "openai"` | OpenAI API key |
| `OPENAI_API_BASE` | Optional | Overrides `model.api_base_url` |
| `ANTHROPIC_API_KEY` | `api_type = "anthropic"` | Anthropic API key |
