"""Stage-specific automated Emfatic/DSML quality metrics.

The evaluator is intentionally auditable. It parses the subset of Emfatic used
by the AUV artefacts, expands inherited features, and then matches classes,
attributes, and references against a reference metamodel using:

1. exact/canonical name equality;
2. optional alias tables for reviewer-auditable semantic equivalence;
3. conservative string similarity for partial matches.

It does not try to prove full metamodel equivalence. The goal is to replace
manual counting with a repeatable first pass and to emit match details that can
be inspected when semantic equivalence is debatable.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Mapping


_CLASS_RE = re.compile(
    r"""
    (?P<abstract>abstract\s+)?
    class\s+(?P<name>[A-Za-z_][\w]*)
    (?:\s+extends\s+(?P<super>[A-Za-z_][\w]*(?:\s*,\s*[A-Za-z_][\w]*)*))?
    \s*\{
    (?P<body>[^{}]*)
    \}
    """,
    re.VERBOSE | re.DOTALL,
)

_FEATURE_RE = re.compile(
    r"""
    (?P<kind>attr|val|ref)\s+
    (?P<type>[A-Za-z_][\w]*)
    (?:\[(?P<bound>[^\]]+)\])?
    \s+
    (?P<name>[A-Za-z_][\w]*)
    \s*;?
    """,
    re.VERBOSE,
)

_NON_ALNUM_RE = re.compile(r"[^0-9a-z]+")
_PLURAL_SUFFIX_RE = re.compile(r"(?<!s)s$")


@dataclass(frozen=True)
class Feature:
    owner: str
    kind: str
    name: str
    type_name: str
    upper: str
    containment: bool
    inherited_from: str = ""

    @property
    def key(self) -> str:
        return f"{self.owner}.{self.name}"


@dataclass
class ClassDef:
    name: str
    abstract: bool
    supertypes: list[str] = field(default_factory=list)
    features: list[Feature] = field(default_factory=list)


@dataclass(frozen=True)
class Match:
    kind: str
    pred: str
    ref: str
    score: float
    reason: str


@dataclass(frozen=True)
class PRF:
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class EmfaticQuality:
    path: str
    run_id: str
    syntax_ok: float
    syntax_error_count: int
    syntax_warning_count: int
    parse_ok: float
    pred_classes: int
    ref_classes: int
    pred_attrs: int
    ref_attrs: int
    pred_refs: int
    ref_refs: int
    class_precision: float
    class_recall: float
    class_f1: float
    attr_precision: float
    attr_recall: float
    attr_f1: float
    ref_precision: float
    ref_recall: float
    ref_f1: float
    macro_f1: float
    weighted_f1: float
    conditional_weighted_f1: float | None
    end_to_end_weighted_f1: float
    extra_classes: str
    missing_classes: str
    error: str = ""

    def as_row(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "syntax_ok": self.syntax_ok,
            "syntax_error_count": self.syntax_error_count,
            "syntax_warning_count": self.syntax_warning_count,
            "parse_ok": self.parse_ok,
            "pred_classes": self.pred_classes,
            "ref_classes": self.ref_classes,
            "pred_attrs": self.pred_attrs,
            "ref_attrs": self.ref_attrs,
            "pred_refs": self.pred_refs,
            "ref_refs": self.ref_refs,
            "class_precision": self.class_precision,
            "class_recall": self.class_recall,
            "class_f1": self.class_f1,
            "attr_precision": self.attr_precision,
            "attr_recall": self.attr_recall,
            "attr_f1": self.attr_f1,
            "ref_precision": self.ref_precision,
            "ref_recall": self.ref_recall,
            "ref_f1": self.ref_f1,
            "macro_f1": self.macro_f1,
            "weighted_f1": self.weighted_f1,
            "conditional_weighted_f1": "" if self.conditional_weighted_f1 is None else self.conditional_weighted_f1,
            "end_to_end_weighted_f1": self.end_to_end_weighted_f1,
            "extra_classes": self.extra_classes,
            "missing_classes": self.missing_classes,
            "path": self.path,
            "error": self.error,
        }


def canonical(value: object) -> str:
    text = str(value or "").strip().casefold()
    text = _NON_ALNUM_RE.sub("", text)
    return _PLURAL_SUFFIX_RE.sub("", text)


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, canonical(a), canonical(b)).ratio()


def load_aliases(path: Path | None) -> dict[str, dict[str, str]]:
    """Load aliases grouped by class/feature/type.

    Shape:
        {
          "classes": {"Canonical": ["Alias"]},
          "features": {"Canonical": ["Alias"]},
          "types": {"Canonical": ["Alias"]}
        }
    """
    result = {"classes": {}, "features": {}, "types": {}}
    if path is None:
        return result
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for group in result:
        group_data = data.get(group, {})
        if not isinstance(group_data, dict):
            raise ValueError(f"{path}: {group} must be an object")
        for target, aliases in group_data.items():
            target_key = canonical(target)
            result[group][target_key] = target_key
            if not isinstance(aliases, list):
                raise ValueError(f"{path}: aliases for {group}.{target!r} must be a list")
            for alias in aliases:
                result[group][canonical(alias)] = target_key
    return result


def alias_key(value: str, aliases: Mapping[str, str]) -> str:
    key = canonical(value)
    return aliases.get(key, key)


def parse_emfatic_text(text: str) -> dict[str, ClassDef]:
    classes: dict[str, ClassDef] = {}
    for match in _CLASS_RE.finditer(text):
        name = match.group("name")
        supertypes = []
        if match.group("super"):
            supertypes = [s.strip() for s in match.group("super").split(",") if s.strip()]
        cls = ClassDef(name=name, abstract=bool(match.group("abstract")), supertypes=supertypes)
        body = match.group("body") or ""
        for feat in _FEATURE_RE.finditer(body):
            kind = feat.group("kind")
            bound = feat.group("bound") or "1"
            cls.features.append(Feature(
                owner=name,
                kind="attribute" if kind == "attr" else "reference",
                name=feat.group("name"),
                type_name=feat.group("type"),
                upper=bound,
                containment=kind == "val",
            ))
        classes[name] = cls
    return classes


def parse_emfatic_file(path: Path) -> dict[str, ClassDef]:
    text = Path(path).read_text(encoding="utf-8")
    classes = parse_emfatic_text(text)
    if not classes:
        raise ValueError(f"{path}: no classes parsed")
    return expand_inherited_features(classes)


def expand_inherited_features(classes: dict[str, ClassDef]) -> dict[str, ClassDef]:
    cache: dict[str, list[Feature]] = {}

    def inherited_for(class_name: str, seen: set[str] | None = None) -> list[Feature]:
        if class_name in cache:
            return cache[class_name]
        seen = set(seen or set())
        if class_name in seen or class_name not in classes:
            return []
        seen.add(class_name)
        cls = classes[class_name]
        features: list[Feature] = []
        for supertype in cls.supertypes:
            for feat in inherited_for(supertype, seen):
                features.append(Feature(
                    owner=class_name,
                    kind=feat.kind,
                    name=feat.name,
                    type_name=feat.type_name,
                    upper=feat.upper,
                    containment=feat.containment,
                    inherited_from=feat.inherited_from or feat.owner,
                ))
            if supertype in classes:
                for feat in classes[supertype].features:
                    features.append(Feature(
                        owner=class_name,
                        kind=feat.kind,
                        name=feat.name,
                        type_name=feat.type_name,
                        upper=feat.upper,
                        containment=feat.containment,
                        inherited_from=supertype,
                    ))
        cache[class_name] = features
        return features

    expanded: dict[str, ClassDef] = {}
    for name, cls in classes.items():
        expanded[name] = ClassDef(
            name=cls.name,
            abstract=cls.abstract,
            supertypes=list(cls.supertypes),
            features=[*inherited_for(name), *cls.features],
        )
    return expanded


def _name_score(pred: str, ref: str, aliases: Mapping[str, str], threshold: float) -> tuple[float, str]:
    if canonical(pred) == canonical(ref):
        return 1.0, "exact"
    if alias_key(pred, aliases) == alias_key(ref, aliases):
        return 1.0, "alias"
    ratio = similarity(pred, ref)
    if ratio >= threshold:
        return 0.5, f"fuzzy:{ratio:.2f}"
    return 0.0, f"no-match:{ratio:.2f}"


def class_pair_score(pred: ClassDef, ref: ClassDef, aliases: Mapping[str, str], threshold: float) -> tuple[float, str]:
    name_score, reason = _name_score(pred.name, ref.name, aliases, threshold)
    if name_score:
        return name_score, reason
    pred_refs = {canonical(f.name) for f in pred.features if f.kind == "reference"}
    ref_refs = {canonical(f.name) for f in ref.features if f.kind == "reference"}
    if pred_refs and ref_refs and len(pred_refs & ref_refs) / len(pred_refs | ref_refs) >= 0.7:
        return 0.5, "partial-structure"
    return 0.0, reason


def type_compatible(pred_type: str, ref_type: str, aliases: Mapping[str, str]) -> bool:
    if canonical(pred_type) == canonical(ref_type):
        return True
    return alias_key(pred_type, aliases) == alias_key(ref_type, aliases)


def feature_pair_score(
    pred: Feature,
    ref: Feature,
    class_matches: Mapping[str, str],
    feature_aliases: Mapping[str, str],
    type_aliases: Mapping[str, str],
    threshold: float,
) -> tuple[float, str]:
    if class_matches.get(pred.owner) != ref.owner:
        return 0.0, "owner-mismatch"
    name_score, reason = _name_score(pred.name, ref.name, feature_aliases, threshold)
    if not name_score:
        return 0.0, reason
    if type_compatible(pred.type_name, ref.type_name, type_aliases):
        return name_score, reason
    # Keep containment differences out of the hard score because requirements
    # usually do not specify ref vs val explicitly; type mismatch is partial.
    return min(name_score, 0.5), f"{reason}+type-partial"


def greedy_match(
    pred_items: list,
    ref_items: list,
    score_fn,
    kind: str,
) -> tuple[list[Match], PRF]:
    pairs: list[tuple[float, str, int, int]] = []
    for i, pred in enumerate(pred_items):
        for j, ref in enumerate(ref_items):
            score, reason = score_fn(pred, ref)
            if score > 0:
                pairs.append((score, reason, i, j))
    pairs.sort(key=lambda p: (-p[0], p[2], p[3]))
    used_pred: set[int] = set()
    used_ref: set[int] = set()
    matches: list[Match] = []
    for score, reason, i, j in pairs:
        if i in used_pred or j in used_ref:
            continue
        used_pred.add(i)
        used_ref.add(j)
        pred_name = pred_items[i].name if hasattr(pred_items[i], "name") else pred_items[i].key
        ref_name = ref_items[j].name if hasattr(ref_items[j], "name") else ref_items[j].key
        matches.append(Match(kind, pred_name, ref_name, score, reason))
    precision = sum(m.score for m in matches) / len(pred_items) if pred_items else (1.0 if not ref_items else 0.0)
    recall = sum(m.score for m in matches) / len(ref_items) if ref_items else (1.0 if not pred_items else 0.0)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return matches, PRF(precision, recall, f1)


def score_files(
    pred_path: Path,
    ref_path: Path,
    aliases: dict[str, dict[str, str]] | None = None,
    fuzzy_threshold: float = 0.88,
    syntax_ok: bool = True,
    syntax_error_count: int = 0,
    syntax_warning_count: int = 0,
    syntax_error: str = "",
) -> tuple[EmfaticQuality, list[Match]]:
    aliases = aliases or {"classes": {}, "features": {}, "types": {}}
    run_id = Path(pred_path).parent.name
    try:
        pred_classes = parse_emfatic_file(pred_path)
        ref_classes = parse_emfatic_file(ref_path)
    except Exception as ex:
        return EmfaticQuality(
            path=str(Path(pred_path).resolve()),
            run_id=run_id,
            syntax_ok=1.0 if syntax_ok else 0.0,
            syntax_error_count=syntax_error_count,
            syntax_warning_count=syntax_warning_count,
            parse_ok=0.0,
            pred_classes=0,
            ref_classes=0,
            pred_attrs=0,
            ref_attrs=0,
            pred_refs=0,
            ref_refs=0,
            class_precision=0.0,
            class_recall=0.0,
            class_f1=0.0,
            attr_precision=0.0,
            attr_recall=0.0,
            attr_f1=0.0,
            ref_precision=0.0,
            ref_recall=0.0,
            ref_f1=0.0,
            macro_f1=0.0,
            weighted_f1=0.0,
            conditional_weighted_f1=0.0 if syntax_ok else None,
            end_to_end_weighted_f1=0.0,
            extra_classes="",
            missing_classes="",
            error="; ".join(part for part in (syntax_error, str(ex)) if part),
        ), []

    pred_class_items = list(pred_classes.values())
    ref_class_items = list(ref_classes.values())
    class_matches, class_prf = greedy_match(
        pred_class_items,
        ref_class_items,
        lambda p, r: class_pair_score(p, r, aliases.get("classes", {}), fuzzy_threshold),
        "class",
    )
    class_map = {m.pred: m.ref for m in class_matches if m.score > 0}

    pred_attrs = [f for cls in pred_classes.values() for f in cls.features if f.kind == "attribute"]
    ref_attrs = [f for cls in ref_classes.values() for f in cls.features if f.kind == "attribute"]
    pred_refs = [f for cls in pred_classes.values() for f in cls.features if f.kind == "reference"]
    ref_refs = [f for cls in ref_classes.values() for f in cls.features if f.kind == "reference"]

    attr_matches, attr_prf = greedy_match(
        pred_attrs,
        ref_attrs,
        lambda p, r: feature_pair_score(
            p, r, class_map, aliases.get("features", {}), aliases.get("types", {}), fuzzy_threshold
        ),
        "attribute",
    )
    ref_matches, ref_prf = greedy_match(
        pred_refs,
        ref_refs,
        lambda p, r: feature_pair_score(
            p, r, class_map, aliases.get("features", {}), aliases.get("types", {}), fuzzy_threshold
        ),
        "reference",
    )

    macro_f1 = (class_prf.f1 + attr_prf.f1 + ref_prf.f1) / 3
    total_ref = len(ref_class_items) + len(ref_attrs) + len(ref_refs)
    weighted_f1 = (
        (class_prf.f1 * len(ref_class_items) + attr_prf.f1 * len(ref_attrs) + ref_prf.f1 * len(ref_refs)) / total_ref
        if total_ref else 0.0
    )

    matched_pred_classes = {m.pred for m in class_matches}
    matched_ref_classes = {m.ref for m in class_matches}
    extra = sorted(c.name for c in pred_class_items if c.name not in matched_pred_classes)
    missing = sorted(c.name for c in ref_class_items if c.name not in matched_ref_classes)

    quality = EmfaticQuality(
        path=str(Path(pred_path).resolve()),
        run_id=run_id,
        syntax_ok=1.0 if syntax_ok else 0.0,
        syntax_error_count=syntax_error_count,
        syntax_warning_count=syntax_warning_count,
        parse_ok=1.0,
        pred_classes=len(pred_class_items),
        ref_classes=len(ref_class_items),
        pred_attrs=len(pred_attrs),
        ref_attrs=len(ref_attrs),
        pred_refs=len(pred_refs),
        ref_refs=len(ref_refs),
        class_precision=class_prf.precision,
        class_recall=class_prf.recall,
        class_f1=class_prf.f1,
        attr_precision=attr_prf.precision,
        attr_recall=attr_prf.recall,
        attr_f1=attr_prf.f1,
        ref_precision=ref_prf.precision,
        ref_recall=ref_prf.recall,
        ref_f1=ref_prf.f1,
        macro_f1=macro_f1,
        weighted_f1=weighted_f1,
        conditional_weighted_f1=weighted_f1 if syntax_ok else None,
        end_to_end_weighted_f1=weighted_f1 if syntax_ok else 0.0,
        extra_classes=";".join(extra),
        missing_classes=";".join(missing),
        error=syntax_error,
    )
    return quality, [*class_matches, *attr_matches, *ref_matches]
