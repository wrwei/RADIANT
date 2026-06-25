"""Single source of truth for MALCOMp pipeline identity.

Each REMEDIATE Phase 2-5 is realised by a Multi-Agent LLM *Layer* (the paper's
word for what the stage classes implement). This module is the ONE place that
records, per Layer: its CLI token, REMEDIATE phase, canonical name, stage class,
config key, agent roster, and traceability artefact. Every runner, the web
bridge, the frontend and base.py's roster assertion read from here instead of
restating this identity. See CONTEXT.md for the canonical vocabulary.

This registry holds the canonical identity (names, CLI tokens, and canonicalised
on-disk filenames). The only remaining legacy tokens are the ``json_tag`` keys
inside the traceability JSON content (term_trace/dsl_trace/...), which stay frozen
because they are parsed from artefact content by the metrics package and MALCOMj.

The roster lists only the group-chat agents (those appended to ``self.agents``
via ``create_agent``); side agents created directly (e.g. the emf layer's
``EOL_Repairer`` repair-loop agent) are intentionally excluded.
"""
from __future__ import annotations

from dataclasses import dataclass

from phases import (
    BehaviourModelCreation,
    ConceptExtraction,
    DSMLCreation,
    EMFModelCreation,
)


@dataclass(frozen=True)
class AgentSpec:
    name: str          # the LLM-visible agent name passed to create_agent(name=...)
    role: str          # the paper's prose role, e.g. "Concept Extraction Agent"
    primary: bool = False   # the generation agent the single-agent baseline uses


@dataclass(frozen=True)
class LayerSpec:
    key: str           # CLI token, e.g. "concept"
    phase: int         # REMEDIATE phase number
    name: str          # paper Layer name, e.g. "Concept Extraction Layer"
    cls: type          # the stage class implementing this Layer
    config_key: str    # the key under `stages:` in config.yaml
    agents: tuple[AgentSpec, ...]
    output_kind: str   # "json" or "code"
    json_tag: str | None = None     # root key of the traceability JSON
    json_file: str | None = None    # traceability JSON filename
    code_file: str | None = None    # code artefact filename
    repeatable: bool = False        # supports run.py --repeat (run_multiple)

    @property
    def agent_names(self) -> tuple[str, ...]:
        return tuple(a.name for a in self.agents)

    @property
    def primary_agent(self) -> AgentSpec:
        for a in self.agents:
            if a.primary:
                return a
        raise ValueError(f"Layer {self.key!r} has no primary agent")


LAYERS: dict[str, LayerSpec] = {
    "concept": LayerSpec(
        key="concept",
        phase=2,
        name="Concept Extraction Layer",
        cls=ConceptExtraction,
        config_key="concept_extraction",
        agents=(
            AgentSpec("Concept_Extraction_Agent", "Concept Extraction Agent", primary=True),
            AgentSpec("Concept_Checker_Agent", "Concept Checker Agent"),
            AgentSpec("Trace_Generation_Agent", "Trace Generation Agent"),
        ),
        output_kind="json",
        json_tag="term_trace",          # FROZEN: on-disk JSON key (metrics + MALCOMj)
        json_file="result_concept_trace.json",  # on-disk filename (metrics + MALCOMj)
        repeatable=True,
    ),
    "dsml": LayerSpec(
        key="dsml",
        phase=3,
        name="DSML Creation Layer",
        cls=DSMLCreation,
        config_key="dsml_creation",
        agents=(
            AgentSpec("DSML_Extraction_Agent", "DSML Extraction Agent", primary=True),
            AgentSpec("DSML_Checker_Agent", "DSML Checker Agent"),
            AgentSpec("DSML_Refactoring_Agent", "DSML Refactoring Agent"),
            AgentSpec("Trace_Generation_Agent", "Trace Generation Agent"),
        ),
        output_kind="code",
        code_file="result_dsml.emf",   # on-disk filename (metrics + MALCOMj)
    ),
    "model": LayerSpec(
        key="model",
        phase=4,
        name="Model Creation Layer",
        cls=EMFModelCreation,
        config_key="emf_model_creation",
        agents=(
            AgentSpec("Model_Creator", "Model Creation Agent", primary=True),
            AgentSpec("Model_Checker", "Model Checker Agent"),
            AgentSpec("Model_Refactorer", "Model Refactoring Agent"),
            AgentSpec("Trace_Generation_Agent", "Trace Generation Agent"),
        ),
        output_kind="code",
        code_file="result_model.eol",
    ),
    "behaviour": LayerSpec(
        key="behaviour",
        phase=5,
        name="Behaviour Model Creation Layer",
        cls=BehaviourModelCreation,
        config_key="behaviour_model_creation",
        agents=(
            AgentSpec("Behaviour_Model_Creation_Agent", "Behaviour Model Creation Agent", primary=True),
            AgentSpec("Behaviour_Checker_Agent", "Behaviour Checker Agent"),
            AgentSpec("Trace_Generation_Agent", "Trace Generation Agent"),
        ),
        output_kind="code",
        code_file="result_behaviour_model.rct",   # on-disk filename (metrics + MALCOMj)
    ),
}
