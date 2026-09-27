"""Stage-specific term-extraction evaluation metrics.

This module evaluates Concept/Term JSON artefacts as structured extraction
outputs, not as plain text. It reports:

* JSON validity: whether the file can be parsed as JSON.
* Schema validity: whether entries have the required term fields.
* Deduplicated vocabulary micro P/R/F1 over concept and instance facts.
* Requirement-linked micro P/R/F1 over
  (GID, Concept, Instance, Instance_of).
* Requirement-linked per-GID macro F1.
* Per-GID exact-set match rate.
* Concept, instance, typed-instance, and instance-type set-level diagnostics.
* Requirement-linked hallucination and omission rates.
* Field-level diagnostic F1 scores that keep requirement context.
* Alias-aware tuple F1 using an optional, auditable alias table.

Together, the three primary metrics separate vocabulary identification from
requirement-to-term traceability and cross-requirement consistency.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


REQUIRED_FIELDS = ("GID", "Concept", "Instance", "Instance_of")
OPTIONAL_TOP_LEVEL_KEYS = ("term_trace", "req", "requirements")
_SEP = "\x1f"
_BLANK_STRINGS = {"", "none", "null", "n/a", "na"}
_NON_ALNUM_RE = re.compile(r"[^0-9a-z]+")


@dataclass(frozen=True)
class PRF:
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int


@dataclass(frozen=True)
class JsonLoadResult:
    valid_json: bool
    entries: list[dict]
    error: str = ""


@dataclass(frozen=True)
class SchemaResult:
    schema_valid: bool
    valid_entry_ratio: float
    valid_entries: int
    invalid_entries: int
    missing_required_fields: int
    non_object_entries: int


@dataclass(frozen=True)
class TermMetrics:
    path: str
    run_id: str
    valid_json: float
    schema_valid: float
    valid_entry_ratio: float
    pred_entries: int
    ref_entries: int
    duplicate_rate: float
    dedup_vocabulary_pred: int
    dedup_vocabulary_ref: int
    dedup_vocabulary_precision: float
    dedup_vocabulary_recall: float
    dedup_vocabulary_f1: float
    requirement_linked_micro_precision: float
    requirement_linked_micro_recall: float
    requirement_linked_micro_f1: float
    requirement_linked_macro_f1: float
    requirement_linked_exact_match_rate: float
    requirement_linked_exact_match_count: int
    requirement_linked_gid_count: int
    requirement_linked_hallucination_rate: float
    requirement_linked_omission_rate: float
    concept_precision: float
    concept_recall: float
    concept_f1: float
    instance_precision: float
    instance_recall: float
    instance_f1: float
    typed_instance_precision: float
    typed_instance_recall: float
    typed_instance_f1: float
    instance_type_precision: float
    instance_type_recall: float
    instance_type_f1: float
    tuple_precision: float
    tuple_recall: float
    tuple_f1: float
    tuple_tp: int
    tuple_fp: int
    tuple_fn: int
    field_gid_f1: float
    field_concept_f1: float
    field_instance_f1: float
    field_instance_of_f1: float
    field_macro_f1: float
    alias_precision: float
    alias_recall: float
    alias_f1: float
    dedup_pred_entries: int
    dedup_ref_entries: int
    dedup_tuple_precision: float
    dedup_tuple_recall: float
    dedup_tuple_f1: float
    dedup_field_macro_f1: float
    dedup_alias_precision: float
    dedup_alias_recall: float
    dedup_alias_f1: float
    error: str = ""

    def as_row(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "valid_json": self.valid_json,
            "schema_valid": self.schema_valid,
            "valid_entry_ratio": self.valid_entry_ratio,
            "pred_entries": self.pred_entries,
            "ref_entries": self.ref_entries,
            "duplicate_rate": self.duplicate_rate,
            "dedup_vocabulary_pred": self.dedup_vocabulary_pred,
            "dedup_vocabulary_ref": self.dedup_vocabulary_ref,
            "dedup_vocabulary_precision": self.dedup_vocabulary_precision,
            "dedup_vocabulary_recall": self.dedup_vocabulary_recall,
            "dedup_vocabulary_f1": self.dedup_vocabulary_f1,
            "requirement_linked_micro_precision": self.requirement_linked_micro_precision,
            "requirement_linked_micro_recall": self.requirement_linked_micro_recall,
            "requirement_linked_micro_f1": self.requirement_linked_micro_f1,
            "requirement_linked_macro_f1": self.requirement_linked_macro_f1,
            "requirement_linked_exact_match_rate": self.requirement_linked_exact_match_rate,
            "requirement_linked_exact_match_count": self.requirement_linked_exact_match_count,
            "requirement_linked_gid_count": self.requirement_linked_gid_count,
            "requirement_linked_hallucination_rate": self.requirement_linked_hallucination_rate,
            "requirement_linked_omission_rate": self.requirement_linked_omission_rate,
            "concept_precision": self.concept_precision,
            "concept_recall": self.concept_recall,
            "concept_f1": self.concept_f1,
            "instance_precision": self.instance_precision,
            "instance_recall": self.instance_recall,
            "instance_f1": self.instance_f1,
            "typed_instance_precision": self.typed_instance_precision,
            "typed_instance_recall": self.typed_instance_recall,
            "typed_instance_f1": self.typed_instance_f1,
            "instance_type_precision": self.instance_type_precision,
            "instance_type_recall": self.instance_type_recall,
            "instance_type_f1": self.instance_type_f1,
            "term_structural_precision": self.tuple_precision,
            "term_structural_recall": self.tuple_recall,
            "term_structural_f1": self.tuple_f1,
            "term_structural_tp": self.tuple_tp,
            "term_structural_fp": self.tuple_fp,
            "term_structural_fn": self.tuple_fn,
            "field_gid_f1": self.field_gid_f1,
            "field_concept_f1": self.field_concept_f1,
            "field_instance_f1": self.field_instance_f1,
            "field_instance_of_f1": self.field_instance_of_f1,
            "term_field_f1": self.field_macro_f1,
            "term_alias_precision": self.alias_precision,
            "term_alias_recall": self.alias_recall,
            "term_alias_f1": self.alias_f1,
            "dedup_pred_entries": self.dedup_pred_entries,
            "dedup_ref_entries": self.dedup_ref_entries,
            "dedup_term_structural_precision": self.dedup_tuple_precision,
            "dedup_term_structural_recall": self.dedup_tuple_recall,
            "dedup_term_structural_f1": self.dedup_tuple_f1,
            "dedup_term_field_f1": self.dedup_field_macro_f1,
            "dedup_term_alias_precision": self.dedup_alias_precision,
            "dedup_term_alias_recall": self.dedup_alias_recall,
            "dedup_term_alias_f1": self.dedup_alias_f1,
            "path": self.path,
            "error": self.error,
        }


def canonical_value(value: object) -> str:
    """Return a deterministic token for term fields.

    This removes representational noise only. It does not infer synonyms.
    """
    if value is None:
        return ""
    text = str(value).strip()
    if text.casefold() in _BLANK_STRINGS:
        return ""
    return _NON_ALNUM_RE.sub("", text.casefold())


def load_aliases(path: Path | None) -> dict[str, str]:
    """Load an alias table and return canonical alias token -> canonical target.

    Expected JSON shape:
        {"CanonicalName": ["Alias A", "Alias B"], ...}
    The canonical name is also mapped to itself.
    """
    if path is None:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: alias table must be a JSON object")
    aliases: dict[str, str] = {}
    for target, values in data.items():
        target_key = canonical_value(target)
        aliases[target_key] = target_key
        if not isinstance(values, list):
            raise ValueError(f"{path}: aliases for {target!r} must be a list")
        for alias in values:
            aliases[canonical_value(alias)] = target_key
    return aliases


def load_json_entries(path: Path) -> JsonLoadResult:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as ex:
        return JsonLoadResult(False, [], str(ex))

    try:
        if isinstance(data, dict):
            for key in OPTIONAL_TOP_LEVEL_KEYS:
                if key in data:
                    entries = data[key]
                    if not isinstance(entries, list):
                        return JsonLoadResult(True, [], f"top-level {key!r} is not a list")
                    return JsonLoadResult(True, list(entries))
            return JsonLoadResult(True, [], "dict has no recognised term-extraction top-level key")
        if isinstance(data, list):
            return JsonLoadResult(True, list(data))
        return JsonLoadResult(True, [], f"unsupported JSON root type: {type(data).__name__}")
    except Exception as ex:
        return JsonLoadResult(True, [], str(ex))


def schema_result(entries: list[object]) -> SchemaResult:
    if not entries:
        return SchemaResult(False, 0.0, 0, 0, 0, 0)

    valid_entries = 0
    missing_required = 0
    non_object = 0
    for entry in entries:
        if not isinstance(entry, dict):
            non_object += 1
            continue
        missing = [field for field in REQUIRED_FIELDS if field not in entry]
        if missing:
            missing_required += len(missing)
            continue
        valid_entries += 1

    invalid_entries = len(entries) - valid_entries
    ratio = valid_entries / len(entries)
    return SchemaResult(
        schema_valid=invalid_entries == 0,
        valid_entry_ratio=ratio,
        valid_entries=valid_entries,
        invalid_entries=invalid_entries,
        missing_required_fields=missing_required,
        non_object_entries=non_object,
    )


def _normalised_entries(entries: Iterable[object]) -> list[dict]:
    out: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        normalised = dict(entry)
        if canonical_value(normalised.get("Concept", "")) == "":
            normalised["Concept"] = normalised.get("Instance_of", "")
        out.append(normalised)
    return out


def _apply_alias(value: object, aliases: Mapping[str, str]) -> str:
    key = canonical_value(value)
    return aliases.get(key, key)


def _key(entry: dict, fields: tuple[str, ...], aliases: Mapping[str, str] | None = None) -> str:
    parts: list[str] = []
    alias_map = aliases or {}
    for field in fields:
        value = entry.get(field, "")
        if field == "Concept" and canonical_value(value) == "":
            value = entry.get("Instance_of", "")
        if field in {"Concept", "Instance", "Instance_of"}:
            parts.append(_apply_alias(value, alias_map))
        else:
            parts.append(canonical_value(value))
    return _SEP.join(parts)


def _prf_from_keys(pred_keys: Iterable[str], ref_keys: Iterable[str]) -> PRF:
    pred_bag = Counter(pred_keys)
    ref_bag = Counter(ref_keys)
    tp = sum((pred_bag & ref_bag).values())
    fp = sum((pred_bag - ref_bag).values())
    fn = sum((ref_bag - pred_bag).values())
    if tp == 0 and fp == 0 and fn == 0:
        return PRF(1.0, 1.0, 1.0, 0, 0, 0)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return PRF(precision, recall, f1, tp, fp, fn)


def vocabulary_set_prf(
    pred_entries: Iterable[object],
    ref_entries: Iterable[object],
    aliases: Mapping[str, str] | None = None,
) -> tuple[PRF, int, int]:
    """Score unique concept and instance facts without requirement IDs."""
    alias_map = aliases or {}

    def vocabulary_facts(entries: Iterable[object]) -> set[str]:
        facts: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            concept = _apply_alias(entry.get("Concept", ""), alias_map)
            instance = _apply_alias(entry.get("Instance", ""), alias_map)
            instance_of = _apply_alias(entry.get("Instance_of", ""), alias_map)
            if concept:
                facts.add(_SEP.join(("concept", concept)))
            if instance:
                facts.add(_SEP.join(("instance", instance, instance_of)))
        return facts

    pred_keys = vocabulary_facts(pred_entries)
    ref_keys = vocabulary_facts(ref_entries)
    return _prf_from_keys(pred_keys, ref_keys), len(pred_keys), len(ref_keys)


def requirement_linked_prf(
    pred_entries: Iterable[object],
    ref_entries: Iterable[object],
) -> tuple[PRF, float]:
    """Score unique strict tuples globally and equally across requirement IDs."""

    def linked_facts(entries: Iterable[object]) -> set[str]:
        facts: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            # A trace entry may omit Concept when Instance_of already provides
            # the type. Use the same fallback as the structural metrics so all
            # term metrics interpret this representation consistently.
            facts.add(_key(entry, REQUIRED_FIELDS))
        return facts

    pred_keys = linked_facts(pred_entries)
    ref_keys = linked_facts(ref_entries)
    micro = _prf_from_keys(pred_keys, ref_keys)
    gids = {
        key.split(_SEP, 1)[0]
        for key in pred_keys | ref_keys
    }
    if not gids:
        return micro, 1.0
    per_gid_f1 = []
    for gid in sorted(gids):
        pred_gid = {key for key in pred_keys if key.split(_SEP, 1)[0] == gid}
        ref_gid = {key for key in ref_keys if key.split(_SEP, 1)[0] == gid}
        per_gid_f1.append(_prf_from_keys(pred_gid, ref_gid).f1)
    return micro, sum(per_gid_f1) / len(per_gid_f1)


def requirement_linked_diagnostics(
    pred_entries: Iterable[object],
    ref_entries: Iterable[object],
) -> tuple[float, int, int]:
    """Return exact-set match rate, exact GID count, and evaluated GID count."""

    def grouped_facts(entries: Iterable[object]) -> dict[str, set[str]]:
        groups: dict[str, set[str]] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            gid = canonical_value(entry.get("GID", ""))
            fact = _key(entry, REQUIRED_FIELDS)
            groups.setdefault(gid, set()).add(fact)
        return groups

    pred_groups = grouped_facts(pred_entries)
    ref_groups = grouped_facts(ref_entries)
    gids = sorted(set(pred_groups) | set(ref_groups))
    if not gids:
        return 1.0, 0, 0
    exact = sum(pred_groups.get(gid, set()) == ref_groups.get(gid, set()) for gid in gids)
    return exact / len(gids), exact, len(gids)


def semantic_diagnostic_prfs(
    pred_entries: Iterable[object],
    ref_entries: Iterable[object],
) -> dict[str, PRF]:
    """Score unique semantic facts without requirement identifiers."""

    def facts(entries: Iterable[object], fields: tuple[str, ...], required: tuple[str, ...]) -> set[str]:
        out: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            values = {field: canonical_value(entry.get(field, "")) for field in fields}
            if any(not values[field] for field in required):
                continue
            out.add(_SEP.join(values[field] for field in fields))
        return out

    definitions = {
        "concept": (("Concept",), ("Concept",)),
        "instance": (("Instance",), ("Instance",)),
        "typed_instance": (("Concept", "Instance"), ("Concept", "Instance")),
        "instance_type": (("Instance", "Instance_of"), ("Instance", "Instance_of")),
    }
    result = {}
    for name, (fields, required) in definitions.items():
        result[name] = _prf_from_keys(
            facts(pred_entries, fields, required),
            facts(ref_entries, fields, required),
        )
    return result


def prf_for_fields(
    pred_entries: list[dict],
    ref_entries: list[dict],
    fields: tuple[str, ...],
    aliases: Mapping[str, str] | None = None,
) -> PRF:
    return _prf_from_keys(
        (_key(entry, fields, aliases) for entry in pred_entries),
        (_key(entry, fields, aliases) for entry in ref_entries),
    )


def duplicate_rate(entries: list[dict]) -> float:
    if not entries:
        return 0.0
    keys = [_key(entry, REQUIRED_FIELDS) for entry in entries]
    unique_count = len(set(keys))
    return (len(keys) - unique_count) / len(keys)


def deduplicate_entries(entries: list[dict]) -> list[dict]:
    """Keep the first occurrence of each strict structural tuple."""
    out: list[dict] = []
    seen: set[str] = set()
    for entry in entries:
        key = _key(entry, REQUIRED_FIELDS)
        if key in seen:
            continue
        seen.add(key)
        out.append(entry)
    return out


def _field_macro_f1(pred_entries: list[dict], ref_entries: list[dict]) -> float:
    gid_prf = prf_for_fields(pred_entries, ref_entries, ("GID",))
    concept_prf = prf_for_fields(pred_entries, ref_entries, ("GID", "Concept"))
    instance_prf = prf_for_fields(pred_entries, ref_entries, ("GID", "Instance"))
    instance_of_prf = prf_for_fields(pred_entries, ref_entries, ("GID", "Instance", "Instance_of"))
    return (gid_prf.f1 + concept_prf.f1 + instance_prf.f1 + instance_of_prf.f1) / 4


def score_file(pred_path: Path, ref_path: Path, aliases: Mapping[str, str] | None = None) -> TermMetrics:
    pred_load = load_json_entries(pred_path)
    ref_load = load_json_entries(ref_path)
    run_id = Path(pred_path).parent.name

    if not pred_load.valid_json:
        return TermMetrics(
            path=str(Path(pred_path).resolve()),
            run_id=run_id,
            valid_json=0.0,
            schema_valid=0.0,
            valid_entry_ratio=0.0,
            pred_entries=0,
            ref_entries=0,
            duplicate_rate=0.0,
            dedup_vocabulary_pred=0,
            dedup_vocabulary_ref=0,
            dedup_vocabulary_precision=0.0,
            dedup_vocabulary_recall=0.0,
            dedup_vocabulary_f1=0.0,
            requirement_linked_micro_precision=0.0,
            requirement_linked_micro_recall=0.0,
            requirement_linked_micro_f1=0.0,
            requirement_linked_macro_f1=0.0,
            requirement_linked_exact_match_rate=0.0,
            requirement_linked_exact_match_count=0,
            requirement_linked_gid_count=0,
            requirement_linked_hallucination_rate=0.0,
            requirement_linked_omission_rate=0.0,
            concept_precision=0.0,
            concept_recall=0.0,
            concept_f1=0.0,
            instance_precision=0.0,
            instance_recall=0.0,
            instance_f1=0.0,
            typed_instance_precision=0.0,
            typed_instance_recall=0.0,
            typed_instance_f1=0.0,
            instance_type_precision=0.0,
            instance_type_recall=0.0,
            instance_type_f1=0.0,
            tuple_precision=0.0,
            tuple_recall=0.0,
            tuple_f1=0.0,
            tuple_tp=0,
            tuple_fp=0,
            tuple_fn=0,
            field_gid_f1=0.0,
            field_concept_f1=0.0,
            field_instance_f1=0.0,
            field_instance_of_f1=0.0,
            field_macro_f1=0.0,
            alias_precision=0.0,
            alias_recall=0.0,
            alias_f1=0.0,
            dedup_pred_entries=0,
            dedup_ref_entries=0,
            dedup_tuple_precision=0.0,
            dedup_tuple_recall=0.0,
            dedup_tuple_f1=0.0,
            dedup_field_macro_f1=0.0,
            dedup_alias_precision=0.0,
            dedup_alias_recall=0.0,
            dedup_alias_f1=0.0,
            error=pred_load.error,
        )
    if not ref_load.valid_json:
        raise ValueError(f"reference JSON is invalid: {ref_load.error}")
    if not ref_load.entries:
        raise ValueError(f"reference has no scorable entries: {ref_load.error}")

    schema = schema_result(pred_load.entries)
    vocabulary_prf, pred_vocabulary_count, ref_vocabulary_count = vocabulary_set_prf(
        pred_load.entries,
        ref_load.entries,
    )
    requirement_linked_micro, requirement_linked_macro = requirement_linked_prf(
        pred_load.entries,
        ref_load.entries,
    )
    exact_rate, exact_count, gid_count = requirement_linked_diagnostics(
        pred_load.entries,
        ref_load.entries,
    )
    semantic_prfs = semantic_diagnostic_prfs(
        _normalised_entries(pred_load.entries),
        _normalised_entries(ref_load.entries),
    )
    pred_entries = _normalised_entries(pred_load.entries)
    ref_entries = _normalised_entries(ref_load.entries)

    tuple_prf = prf_for_fields(pred_entries, ref_entries, REQUIRED_FIELDS)
    gid_prf = prf_for_fields(pred_entries, ref_entries, ("GID",))
    concept_prf = prf_for_fields(pred_entries, ref_entries, ("GID", "Concept"))
    instance_prf = prf_for_fields(pred_entries, ref_entries, ("GID", "Instance"))
    instance_of_prf = prf_for_fields(pred_entries, ref_entries, ("GID", "Instance", "Instance_of"))
    field_macro = (gid_prf.f1 + concept_prf.f1 + instance_prf.f1 + instance_of_prf.f1) / 4
    alias_prf = prf_for_fields(pred_entries, ref_entries, REQUIRED_FIELDS, aliases=aliases)
    dedup_entries = deduplicate_entries(pred_entries)
    dedup_ref_entries = deduplicate_entries(ref_entries)
    dedup_tuple_prf = prf_for_fields(dedup_entries, dedup_ref_entries, REQUIRED_FIELDS)
    dedup_alias_prf = prf_for_fields(dedup_entries, dedup_ref_entries, REQUIRED_FIELDS, aliases=aliases)

    return TermMetrics(
        path=str(Path(pred_path).resolve()),
        run_id=run_id,
        valid_json=1.0,
        schema_valid=1.0 if schema.schema_valid else 0.0,
        valid_entry_ratio=schema.valid_entry_ratio,
        pred_entries=len(pred_entries),
        ref_entries=len(ref_entries),
        duplicate_rate=duplicate_rate(pred_entries),
        dedup_vocabulary_pred=pred_vocabulary_count,
        dedup_vocabulary_ref=ref_vocabulary_count,
        dedup_vocabulary_precision=vocabulary_prf.precision,
        dedup_vocabulary_recall=vocabulary_prf.recall,
        dedup_vocabulary_f1=vocabulary_prf.f1,
        requirement_linked_micro_precision=requirement_linked_micro.precision,
        requirement_linked_micro_recall=requirement_linked_micro.recall,
        requirement_linked_micro_f1=requirement_linked_micro.f1,
        requirement_linked_macro_f1=requirement_linked_macro,
        requirement_linked_exact_match_rate=exact_rate,
        requirement_linked_exact_match_count=exact_count,
        requirement_linked_gid_count=gid_count,
        requirement_linked_hallucination_rate=(
            requirement_linked_micro.fp / (requirement_linked_micro.tp + requirement_linked_micro.fp)
            if requirement_linked_micro.tp + requirement_linked_micro.fp else 0.0
        ),
        requirement_linked_omission_rate=(
            requirement_linked_micro.fn / (requirement_linked_micro.tp + requirement_linked_micro.fn)
            if requirement_linked_micro.tp + requirement_linked_micro.fn else 0.0
        ),
        concept_precision=semantic_prfs["concept"].precision,
        concept_recall=semantic_prfs["concept"].recall,
        concept_f1=semantic_prfs["concept"].f1,
        instance_precision=semantic_prfs["instance"].precision,
        instance_recall=semantic_prfs["instance"].recall,
        instance_f1=semantic_prfs["instance"].f1,
        typed_instance_precision=semantic_prfs["typed_instance"].precision,
        typed_instance_recall=semantic_prfs["typed_instance"].recall,
        typed_instance_f1=semantic_prfs["typed_instance"].f1,
        instance_type_precision=semantic_prfs["instance_type"].precision,
        instance_type_recall=semantic_prfs["instance_type"].recall,
        instance_type_f1=semantic_prfs["instance_type"].f1,
        tuple_precision=tuple_prf.precision,
        tuple_recall=tuple_prf.recall,
        tuple_f1=tuple_prf.f1,
        tuple_tp=tuple_prf.tp,
        tuple_fp=tuple_prf.fp,
        tuple_fn=tuple_prf.fn,
        field_gid_f1=gid_prf.f1,
        field_concept_f1=concept_prf.f1,
        field_instance_f1=instance_prf.f1,
        field_instance_of_f1=instance_of_prf.f1,
        field_macro_f1=field_macro,
        alias_precision=alias_prf.precision,
        alias_recall=alias_prf.recall,
        alias_f1=alias_prf.f1,
        dedup_pred_entries=len(dedup_entries),
        dedup_ref_entries=len(dedup_ref_entries),
        dedup_tuple_precision=dedup_tuple_prf.precision,
        dedup_tuple_recall=dedup_tuple_prf.recall,
        dedup_tuple_f1=dedup_tuple_prf.f1,
        dedup_field_macro_f1=_field_macro_f1(dedup_entries, dedup_ref_entries),
        dedup_alias_precision=dedup_alias_prf.precision,
        dedup_alias_recall=dedup_alias_prf.recall,
        dedup_alias_f1=dedup_alias_prf.f1,
    )
