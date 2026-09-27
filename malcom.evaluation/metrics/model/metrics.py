"""Fact-based evaluation of executed AUV EMF model instances."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


_NON_ALNUM_RE = re.compile(r"[^0-9a-z]+")
FEATURE_CLASS = {
    "robotic_platforms": "RoboticPlatform",
    "roboticPlatform": "RoboticPlatform",
    "roboticPlatforms": "RoboticPlatform",
    "platform": "RoboticPlatform",
    "platforms": "RoboticPlatform",
    "interfaces": "Interface",
    "controllers": "Controller",
    "functions": "Function",
    "preimitive_types": "PrimitiveType",
    "primitiveTypes": "PrimitiveType",
    "composite_types": "CompositeType",
    "compositeTypes": "CompositeType",
    "values": "Value",
    "fields": "Value",
    "events": "Event",
    "parameters": "Value",
}


@dataclass
class Obj:
    key: str
    class_name: str
    name: str = ""
    parent_key: str = ""
    parent_feature: str = ""


@dataclass(frozen=True)
class PRF:
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int


@dataclass(frozen=True)
class ModelScore:
    run_id: str
    source_kind: str
    parse_ok: float
    pred_object_facts: int
    ref_object_facts: int
    pred_attribute_facts: int
    ref_attribute_facts: int
    pred_link_facts: int
    ref_link_facts: int
    object_precision: float
    object_recall: float
    object_f1: float
    attribute_precision: float
    attribute_recall: float
    attribute_f1: float
    link_precision: float
    link_recall: float
    link_f1: float
    micro_precision: float
    micro_recall: float
    micro_f1: float
    macro_f1: float
    error: str = ""

    def as_row(self) -> dict[str, object]:
        return self.__dict__.copy()


def canonical(value: object) -> str:
    return _NON_ALNUM_RE.sub("", str(value or "").strip().casefold())


def load_aliases(path: Path | None) -> dict[str, dict[str, str]]:
    result = {"classes": {}, "features": {}, "values": {}}
    if path is None:
        return result
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for group in result:
        for target, aliases in data.get(group, {}).items():
            target_key = canonical(target)
            result[group][target_key] = target_key
            for alias in aliases:
                result[group][canonical(alias)] = target_key
    return result


def ak(value: str, aliases: Mapping[str, str]) -> str:
    key = canonical(value)
    return aliases.get(key, key)


def local_name(tag: str) -> str:
    return tag.split("}", 1)[-1].split(":", 1)[-1]


def class_for_xml_element(elem: ET.Element, feature_name: str) -> str:
    xsi_type = elem.attrib.get("{http://www.w3.org/2001/XMLSchema-instance}type", "")
    if xsi_type:
        return xsi_type.split(":", 1)[-1]
    tag = local_name(elem.tag)
    if tag[:1].isupper():
        return tag
    return FEATURE_CLASS.get(feature_name, feature_name[:1].upper() + feature_name[1:])


def parse_xml_model(path: Path) -> tuple[dict[str, Obj], list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    tree = ET.parse(path)
    root = tree.getroot()
    objects: dict[str, Obj] = {}
    attr_facts: list[tuple[str, str, str]] = []
    raw_links: list[tuple[str, str, str]] = []
    path_map: dict[str, str] = {}
    def visit(elem: ET.Element, key: str, feature: str, parent_key: str, path_expr: str) -> None:
        class_name = class_for_xml_element(elem, feature)
        name = elem.attrib.get("name", "")
        objects[key] = Obj(key=key, class_name=class_name, name=name, parent_key=parent_key, parent_feature=feature)
        path_map[path_expr] = key
        if parent_key:
            raw_links.append((parent_key, feature, key))
        for attr, value in elem.attrib.items():
            lname = local_name(attr)
            if lname in {"version", "type"}:
                continue
            if value.startswith("/"):
                for target in value.split():
                    raw_links.append((key, lname, target))
            else:
                attr_facts.append((key, lname, value))

        child_counts: Counter[str] = Counter()
        for child in list(elem):
            child_feature = local_name(child.tag)
            idx = child_counts[child_feature]
            child_counts[child_feature] += 1
            child_path = f"{path_expr}/@{child_feature}.{idx}" if path_expr else f"//@{child_feature}.{idx}"
            child_key = f"{key}/{child_feature}.{idx}"
            visit(child, child_key, child_feature, key, child_path)

    if local_name(root.tag) == "XMI":
        for idx, child in enumerate(list(root)):
            visit(child, f"root.{idx}", local_name(child.tag), "", f"/{idx}")
    else:
        visit(root, "root", "root", "", "")
    resolved_links: list[tuple[str, str, str]] = []
    for src, feat, tgt in raw_links:
        resolved_links.append((src, feat, path_map.get(tgt, tgt)))
    return objects, attr_facts, resolved_links


def semantic_ids(objects: dict[str, Obj], aliases: dict[str, dict[str, str]]) -> dict[str, str]:
    cache: dict[str, str] = {}

    def sid(key: str, seen: set[str] | None = None) -> str:
        if key in cache:
            return cache[key]
        obj = objects[key]
        class_key = ak(obj.class_name, aliases["classes"])
        name_key = ak(obj.name or obj.key, aliases["values"])
        own = f"{class_key}:{name_key}"
        if obj.parent_key and obj.parent_key in objects and obj.parent_key != key:
            seen = set(seen or set())
            if key not in seen:
                seen.add(key)
                parent = sid(obj.parent_key, seen)
                feat = ak(obj.parent_feature, aliases["features"])
                own = f"{parent}/{feat}/{own}"
        cache[key] = own
        return own

    return {key: sid(key) for key in objects}


def facts_from_model(
    objects: dict[str, Obj],
    attr_facts: list[tuple[str, str, str]],
    links: list[tuple[str, str, str]],
    aliases: dict[str, dict[str, str]],
) -> dict[str, set[tuple[str, ...]]]:
    ids = semantic_ids(objects, aliases)
    object_facts = {
        ("object", ak(obj.class_name, aliases["classes"]), ids[key])
        for key, obj in objects.items()
    }
    attribute_facts = {
        ("attribute", ids[src], ak(feat, aliases["features"]), ak(value, aliases["values"]))
        for src, feat, value in attr_facts
        if src in ids
    }
    link_facts = {
        ("link", ids[src], ak(feat, aliases["features"]), ids[tgt])
        for src, feat, tgt in links
        if src in ids and tgt in ids
    }
    return {"object": object_facts, "attribute": attribute_facts, "link": link_facts}


def prf(pred: set[tuple[str, ...]], ref: set[tuple[str, ...]]) -> PRF:
    tp = len(pred & ref)
    fp = len(pred - ref)
    fn = len(ref - pred)
    precision = tp / (tp + fp) if (tp + fp) else (1.0 if not ref else 0.0)
    recall = tp / (tp + fn) if (tp + fn) else (1.0 if not pred else 0.0)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return PRF(precision, recall, f1, tp, fp, fn)


def score_generated(
    pred_path: Path,
    ref_model_path: Path,
    aliases: dict[str, dict[str, str]],
    source_kind: str | None = None,
) -> ModelScore:
    run_id = Path(pred_path).parent.name
    source = source_kind or "model_xml"
    try:
        ref_objects, ref_attrs, ref_links = parse_xml_model(ref_model_path)
        pred_objects, pred_attrs, pred_links = parse_xml_model(pred_path)

        ref_facts = facts_from_model(ref_objects, ref_attrs, ref_links, aliases)
        pred_facts = facts_from_model(pred_objects, pred_attrs, pred_links, aliases)
        obj_prf = prf(pred_facts["object"], ref_facts["object"])
        attr_prf = prf(pred_facts["attribute"], ref_facts["attribute"])
        link_prf = prf(pred_facts["link"], ref_facts["link"])
        pred_all = set().union(*pred_facts.values())
        ref_all = set().union(*ref_facts.values())
        micro = prf(pred_all, ref_all)
        macro_f1 = (obj_prf.f1 + attr_prf.f1 + link_prf.f1) / 3
        return ModelScore(
            run_id=run_id,
            source_kind=source,
            parse_ok=1.0,
            pred_object_facts=len(pred_facts["object"]),
            ref_object_facts=len(ref_facts["object"]),
            pred_attribute_facts=len(pred_facts["attribute"]),
            ref_attribute_facts=len(ref_facts["attribute"]),
            pred_link_facts=len(pred_facts["link"]),
            ref_link_facts=len(ref_facts["link"]),
            object_precision=obj_prf.precision,
            object_recall=obj_prf.recall,
            object_f1=obj_prf.f1,
            attribute_precision=attr_prf.precision,
            attribute_recall=attr_prf.recall,
            attribute_f1=attr_prf.f1,
            link_precision=link_prf.precision,
            link_recall=link_prf.recall,
            link_f1=link_prf.f1,
            micro_precision=micro.precision,
            micro_recall=micro.recall,
            micro_f1=micro.f1,
            macro_f1=macro_f1,
        )
    except Exception as ex:
        return ModelScore(
            run_id=run_id,
            source_kind=source,
            parse_ok=0.0,
            pred_object_facts=0,
            ref_object_facts=0,
            pred_attribute_facts=0,
            ref_attribute_facts=0,
            pred_link_facts=0,
            ref_link_facts=0,
            object_precision=0.0,
            object_recall=0.0,
            object_f1=0.0,
            attribute_precision=0.0,
            attribute_recall=0.0,
            attribute_f1=0.0,
            link_precision=0.0,
            link_recall=0.0,
            link_f1=0.0,
            micro_precision=0.0,
            micro_recall=0.0,
            micro_f1=0.0,
            macro_f1=0.0,
            error=str(ex),
        )
