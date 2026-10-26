"""Offline CPU comparison; CSV input is unchanged, no Oracle/network access.

Pass --csv FILE --profile default|old_demo|demo|expanded --output REPORT.json.
Disagreements with learned rules are not confirmed ground-truth errors.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import io
import json
import logging
import platform
import sys
import time
from importlib.metadata import version
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def blocked(*_args, **_kwargs):
    raise RuntimeError("Database and network access are disabled in this benchmark.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", choices=("default", "old_demo", "demo", "expanded"), default="default")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    with args.csv.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        values = list(reader)
    if any(len(row) != len(header) for row in values):
        raise ValueError("The CSV must have one header row and equal-width data rows.")
    labels = {f"C{i + 1:03d}": label for i, label in enumerate(header)}
    columns = [{"name": name, "dataType": "VARCHAR2"} for name in labels]
    rows = [dict(zip(labels, record)) for record in values]
    demo = {"maxRows": 10000, "maxColumns": 100, "maxFeatures": 2048,
            "treeMaxDepth": 4, "maxTargets": 24, "maxRules": 32,
            "maxContinuousTargets": 12, "maxContinuousRules": 16,
            "maxFormulaFeatures": 3, "maxConditionalGroups": 4}
    profiles = {"default": {}, "old_demo": demo,
                "demo": {**demo, "maxFormulaFeatures": 6, "formulaSqrtEnabled": True},
                "expanded": {"maxColumns": 100, "maxFeatures": 2048, "maxTargets": 64, "maxRules": 128,
                             "maxContinuousTargets": 32, "maxContinuousRules": 128,
                             "maxFormulaFeatures": 6, "formulaSqrtEnabled": True}}
    options = {**profiles[args.profile], "randomSeed": args.seed}
    logging.disable(logging.CRITICAL)
    with (patch("dotenv.load_dotenv", return_value=False), patch("oracledb.connect", side_effect=blocked),
          patch("oracledb.create_pool", side_effect=blocked), patch("socket.create_connection", side_effect=blocked),
          patch("socket.socket.connect", side_effect=blocked), patch("logging.FileHandler._open", lambda _: io.StringIO())):
        from backend.services.mixed_pattern_algorithm import analyze_pattern_rows, evaluate_pattern_predicate
        started = time.perf_counter()
        result = analyze_pattern_rows(rows, columns, options)
        seconds = time.perf_counter() - started
        sample = [rows[item["rowIndex"]] for item in result["rows"]]
        rules = []
        for rule in result["rules"]:
            applicable = [row for row in sample if evaluate_pattern_predicate(rule["predicate"], row)]
            different = sum(not evaluate_pattern_predicate(rule["resultPredicate"], row) for row in applicable)
            text = rule["fullText"]
            for name, label in labels.items():
                text = text.replace(name, label)
            rules.append({"kind": rule["resultKind"], "text": text, "target": labels[rule["resultColumn"]],
                          "trainingConfidence": rule["confidence"], "validation": rule["validation"],
                          "appliedSampleRows": len(applicable), "sampleViolations": different,
                          "condition": rule["predicate"], "result": rule["resultPredicate"]})
    report = {"profile": args.profile, "options": options, "seed": args.seed,
              "inputSha256": hashlib.sha256(args.csv.read_bytes()).hexdigest(),
              "sourceRows": len(rows), "sampleRows": len(sample), "sourceColumns": len(columns),
              "seconds": round(seconds, 3), "cpu": platform.processor(), "python": platform.python_version(),
              "packages": {name: version(name) for name in ("numpy", "scikit-learn")},
              "formulaCount": sum(rule["kind"] == "FORMULA" for rule in rules),
              "conditionCount": sum(rule["kind"] != "FORMULA" for rule in rules),
              "rules": rules, "metrics": result["metrics"], "warnings": result["warnings"],
              "scope": "CPU offline engine; VARCHAR2 original strings; disagreements are not confirmed errors"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("profile", "seconds", "formulaCount", "conditionCount", "sourceRows", "sourceColumns")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
