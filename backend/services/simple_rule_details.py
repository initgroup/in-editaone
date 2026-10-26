"""Bounded drill-down data evaluated with the published rule, without refitting."""
import json
import math
import random

from backend.services.mixed_pattern_algorithm import evaluate_pattern_predicate
from backend.services.mixed_continuous_algorithm import evaluate_formula_expression
from backend.services.mixed_numeric import parse_numeric_text

MAX_DETAIL_ROWS = 120
MAX_DETAIL_BYTES = 128 * 1024
MAX_CELL_CHARS = 160


def _references(node):
    if not isinstance(node, dict):
        return set()
    names = {node["column"]} if "column" in node else set()
    for value in node.values():
        if isinstance(value, dict):
            names.update(_references(value))
        elif isinstance(value, list):
            for child in value:
                names.update(_references(child))
    return names


def _number(value, numeric_text=False):
    try:
        parsed = parse_numeric_text(value) if numeric_text else value
        result = float(parsed)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def rule_reference_columns(rule):
    return _references(rule["predicate"]) | _references(rule["resultPredicate"])


def count_rule_violations(rule, rows):
    """Count frozen-rule disagreements before display limits, without building records."""
    return sum(1 for row in rows if evaluate_pattern_predicate(rule["predicate"], row)
               and not evaluate_pattern_predicate(rule["resultPredicate"], row))


def build_rule_detail(rule, rows, partitions, labels, *, seed):
    """Detect with the frozen rule across the analyzed sample, without refitting.

    Selection-validation evidence is counted separately. Neither the sampled
    display records nor the all-sample detection rate are new accuracy scores.
    """
    formula = rule["resultKind"] == "FORMULA"
    consequent = rule["resultPredicate"]
    target = rule["resultColumn"]
    names = sorted(rule_reference_columns(rule) - {target})
    names = [name for name in names if name in labels]
    stats = {"applied": 0, "matched": 0, "different": 0, "unscorable": 0}
    validation_stats = dict(stats)
    validation_indices = {item["rowIndex"] for item in partitions if item["partition"] == "VALIDATION"}
    matching, different = [], []
    for index, row in enumerate(rows):
        if not evaluate_pattern_predicate(rule["predicate"], row):
            continue
        matched = evaluate_pattern_predicate(consequent, row)
        expected = evaluate_formula_expression(consequent["expression"], row) if formula else None
        actual = _number(row.get(target), consequent.get("numericText", False)) if formula else None
        status = "MATCH" if matched else "UNSCORABLE" if formula and (expected is None or actual is None) else "DIFFERENT"
        for counts in ([stats, validation_stats] if index in validation_indices else [stats]):
            counts["applied"] += 1
            counts["matched" if matched else "different"] += 1
            counts["unscorable"] += status == "UNSCORABLE"
        record = (index, status, expected, actual)
        (matching if matched else different).append(record)

    rng = random.Random(seed)
    rng.shuffle(matching)
    rng.shuffle(different)
    # Include disagreements even when they are rare. These are display records,
    # never the denominator of the published validation rate.
    difference_count = min(len(different), MAX_DETAIL_ROWS // 2)
    match_count = min(len(matching), MAX_DETAIL_ROWS - difference_count)
    difference_count = min(len(different), MAX_DETAIL_ROWS - match_count)
    selected = different[:difference_count] + matching[:match_count]
    records, byte_count = [], 0
    for index, status, expected, actual in selected:
        row = rows[index]
        raw_values = {name: str(row.get(name, "")) for name in names + [target]}
        clipped = {name: value[:MAX_CELL_CHARS] for name, value in raw_values.items()}
        residual = actual - expected if actual is not None and expected is not None else None
        record = {"id": index, "sourceRow": row.get("__source_row__", index + 1),
                  "status": status, "values": clipped, "expected": expected, "actual": actual,
                  "residual": residual if residual is not None and math.isfinite(residual) else None,
                  "truncated": any(len(value) > MAX_CELL_CHARS for value in raw_values.values())}
        size = len(json.dumps(record, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        if byte_count + size > MAX_DETAIL_BYTES:
            break
        records.append(record)
        byte_count += size
    records.sort(key=lambda record: record["sourceRow"])
    return {"cohort": "ANALYZED_SAMPLE", "scannedRows": len(rows), "stats": stats,
            "validationCohort": "SELECTION_VALIDATION", "validationStats": validation_stats,
            "target": {"key": target, "label": labels[target]},
            "inputs": [{"key": name, "label": labels[name]} for name in names],
            "rows": records, "shownRows": len(records), "rowLimit": MAX_DETAIL_ROWS,
            "sampling": "MATCH_STATUS_STRATIFIED", "truncatedCells": any(record["truncated"] for record in records)}
