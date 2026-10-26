"""Bounded file-only discovery for the mobile demo; no Target DB writes."""
from __future__ import annotations

import csv
import random
import re
import secrets
import time
from pathlib import Path
from zipfile import BadZipFile, ZipFile
from xml.etree.ElementTree import ParseError

from fastapi import HTTPException

from backend.services.ml_analysis_service import _limit_ml_concurrency
from backend.services.mixed_pattern_algorithm import analyze_pattern_rows
from backend.services.mixed_continuous_algorithm import formula_expression_text
from backend.services.simple_rule_details import build_rule_detail, count_rule_violations, rule_reference_columns

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_SOURCE_ROWS = 200_000
MAX_COLUMNS = 100
MAX_SAMPLE_ROWS = 10_000
# Account for Python string/object overhead in a 10,000-row, 100-column sample.
MAX_SAMPLE_BYTES = 128 * 1024 * 1024
MIN_ROWS = 32
TOP_RULES = 5


def reject(code, message, status=400):
    raise HTTPException(status, {"code": code, "message": message})


def _file_options(stream, filename):
    from backend.routers.M02001 import resolve_upload_encoding

    extension = Path(filename).suffix.lower()
    if extension not in {".csv", ".tsv", ".xlsx", ".xlsm"}:
        reject("FILE_TYPE", "CSV, TSV, XLSX 파일을 선택해 주세요.")
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(0)
    if not size or size > MAX_FILE_BYTES:
        reject("FILE_SIZE", "비어 있지 않은 20MB 이하 파일을 선택해 주세요.", 413 if size else 400)
    if extension in {".xlsx", ".xlsm"}:
        try:
            with ZipFile(stream) as archive:
                if len(archive.infolist()) > 2048 or sum(item.file_size for item in archive.infolist()) > 100 * 1024 * 1024:
                    reject("EXCEL_SIZE", "Excel 내부 데이터가 데모 범위를 넘습니다. 시트나 행을 줄여 주세요.", 413)
        except BadZipFile:
            reject("FILE_FORMAT", "Excel 파일을 읽을 수 없습니다. XLSX 형식으로 다시 저장해 주세요.")
        finally:
            stream.seek(0)
        return "excel", ",", None
    encoding = resolve_upload_encoding(stream, "csv", "auto")
    sample = stream.read(128 * 1024).decode(encoding, errors="replace")
    stream.seek(0)
    delimiter = "\t" if extension == ".tsv" else ","
    if extension == ".csv":
        try:
            delimiter = csv.Sniffer().sniff(sample[:8192], delimiters=",;\t").delimiter
        except csv.Error:
            pass
    return "csv", delimiter, encoding


def read_sample(stream, filename, *, seed):
    """Algorithm R samples the entire source uniformly, including its last row."""
    from backend.routers.M02001 import iter_upload_raw_rows, is_non_empty_row, close_row_iterator, stringify_cell

    file_type, delimiter, encoding = _file_options(stream, filename)
    iterator = iter_upload_raw_rows(stream, filename, file_type, delimiter, "", encoding)
    rng = random.Random(seed)
    header, sample, retained_bytes, total = None, [], 0, 0
    source_columns = 0
    try:
        for physical_row, raw in enumerate(iterator, 1):
            if not is_non_empty_row(raw):
                continue
            if header is None:
                source_columns = len(raw)
                header = [stringify_cell(value).strip() for value in raw[:MAX_COLUMNS]]
                if len(header) < 2:
                    reject("COLUMN_COUNT", "컬럼은 최소 2개여야 합니다. 첫 행의 컬럼명과 CSV 구분자를 확인해 주세요.")
                if any(not value or len(value) > 80 for value in header) or len({value.casefold() for value in header}) != len(header):
                    reject("HEADER", "첫 행에는 빈 칸·중복 없이 컬럼명을 한 줄로 넣어 주세요. 여러 줄 헤더는 한 줄로 합쳐 주세요.")
                if all(re.fullmatch(r"[-+]?\d+(?:\.\d+)?", value) for value in header):
                    reject("HEADER", "첫 행이 숫자 데이터로 보입니다. 첫 행에 컬럼명을 넣어 주세요.")
                continue
            if len(raw) > source_columns:
                reject("ROW_WIDTH", f"{physical_row}행의 컬럼 수가 헤더보다 많습니다. 구분자와 헤더를 확인해 주세요.")
            row = [stringify_cell(value) for value in raw[:len(header)]]
            if [value.strip() for value in row] == header:
                reject("HEADER", f"{physical_row}행에 컬럼명이 반복됩니다. 헤더는 첫 행 한 줄만 남겨 주세요.")
            row += [""] * (len(header) - len(row))
            if any(len(value.encode("utf-8")) > 4000 for value in row):
                reject("CELL_SIZE", f"{physical_row}행에 4,000바이트를 넘는 셀이 있습니다. 긴 텍스트를 줄여 주세요.")
            total += 1
            if total > MAX_SOURCE_ROWS:
                reject("SOURCE_ROWS", "데모는 원본 20만 행까지 지원합니다. 더 큰 파일은 기존 퀵 에디팅을 이용해 주세요.")
            index = total - 1 if total <= MAX_SAMPLE_ROWS else rng.randrange(total)
            if index < MAX_SAMPLE_ROWS:
                size = 128 + sum(96 + len(value.encode("utf-8")) for value in row)
                if index < len(sample):
                    retained_bytes -= sample[index][1]
                    sample[index] = (row, size, total)
                else:
                    sample.append((row, size, total))
                retained_bytes += size
                if retained_bytes > MAX_SAMPLE_BYTES:
                    reject("SAMPLE_MEMORY", "표본의 텍스트 양이 데모 한도를 넘습니다. 긴 텍스트 컬럼을 줄여 주세요.", 413)
    except (csv.Error, UnicodeError, ValueError, KeyError, IndexError, BadZipFile, ParseError) as error:
        raise HTTPException(400, {"code": "FILE_FORMAT", "message": "파일을 읽을 수 없습니다. CSV 또는 XLSX 형식과 셀 내용을 확인해 주세요."}) from error
    finally:
        close_row_iterator(iterator)
        stream.seek(0)
    if total < MIN_ROWS:
        reject("TOO_FEW_ROWS", f"헤더를 제외한 데이터가 {total:,}행입니다. 최소 {MIN_ROWS}행이 필요합니다. 수식 데모에는 200행 이상을 권장합니다.")
    rng.shuffle(sample)
    names = [f"C{index:03d}" for index in range(1, len(header) + 1)]
    rows = [dict(zip(names, values), __source_row__=source_row) for values, _size, source_row in sample]
    columns = [{"COLUMN_NAME": name, "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 4000} for name in names]
    return rows, columns, dict(zip(names, header)), total, source_columns


def _column_scope(columns, source_columns):
    return {"columns": len(columns), "sourceColumns": source_columns,
            "columnLimit": MAX_COLUMNS, "omittedColumns": source_columns - len(columns),
            "columnSelection": "FIRST_COLUMNS"}


def inspect_file(stream, filename):
    rows, columns, _labels, total, source_columns = read_sample(stream, filename, seed=0)
    return {"status": "success", "data": {"sourceRows": total, "sampleRows": len(rows), **_column_scope(columns, source_columns)}}


def _label_ast(node, labels):
    if isinstance(node, dict):
        return {key: labels.get(value, value) if key == "column" else _label_ast(value, labels) for key, value in node.items()}
    if isinstance(node, list):
        return [_label_ast(value, labels) for value in node]
    return node


def _condition_text(node, labels):
    op = node["operator"]
    if op in {"AND", "OR"}:
        return "(" + (" 그리고 " if op == "AND" else " 또는 ").join(_condition_text(child, labels) for child in node["conditions"]) + ")"
    name = labels.get(node["column"], node["column"])
    if op in {"IS_NULL", "NOT_NULL"}:
        return f"{name} {'값 없음' if op == 'IS_NULL' else '값 있음'}"
    value = str(node.get("value", ""))
    return f"{name} {op.replace('!=', '≠').replace('<=', '≤')} {value}"


def _present_rule(rule, labels):
    formula = rule["resultKind"] == "FORMULA"
    consequent = rule["resultPredicate"]
    validation = rule.get("validation", {})
    result = (labels[rule["resultColumn"]] + " ≈ " + formula_expression_text(_label_ast(consequent["expression"], labels))
              if formula else _condition_text(consequent, labels))
    return {
        "id": rule["ruleId"], "kind": "FORMULA" if formula else "CONDITION", "source": "MIXED_PATTERN",
        "condition": _condition_text(rule["predicate"], labels), "result": result,
        "validationConfidence": validation.get("confidence"),
        "validationRows": validation.get("conditionCount", 0),
        "supportRows": rule.get("supportCount", 0),
        "absoluteTolerance": consequent.get("absoluteTolerance") if formula else None,
        "relativeTolerance": consequent.get("relativeTolerance") if formula else None,
        "hasCondition": _has_value_condition(rule["predicate"]),
    }


def _has_value_condition(predicate):
    if predicate["operator"] in {"AND", "OR"}:
        return any(_has_value_condition(child) for child in predicate["conditions"])
    return predicate["operator"] != "NOT_NULL"


@_limit_ml_concurrency
def analyze_file(stream, filename):
    started = time.monotonic()
    seed = secrets.randbits(32)
    rows, columns, labels, total, source_columns = read_sample(stream, filename, seed=seed)
    excluded = [name for name, label in labels.items() if label.upper() in {"ID", "ROW_ID", "FILE_ROW_NO", "UUID", "번호", "일련번호"}]
    options = {
        "maxRows": MAX_SAMPLE_ROWS, "maxColumns": MAX_COLUMNS, "maxFeatures": 2048,
        "randomSeed": seed, "treeMaxDepth": 4, "maxTargets": 24, "maxRules": 32,
        "maxContinuousTargets": 12, "maxContinuousRules": 16, "maxFormulaFeatures": 6,
        "formulaSqrtEnabled": True,
        "maxConditionalGroups": 4, "excludeColumns": excluded,
    }
    analysis = analyze_pattern_rows(rows, columns, options)
    families = {"FORMULA": [], "CONDITION": []}
    # Detect every validated candidate before limiting the display. The detection
    # cohort is the full analyzed sample, not a new fit or validation score.
    candidates = [(rule, count_rule_violations(rule, rows)) for rule in analysis["rules"]]
    ranked = [rule for rule, count in sorted(candidates, key=lambda item: (
        -item[1], -item[0]["confidence"], -item[0]["supportCount"], item[0].get("formulaComplexity", 0), item[0]["ruleId"])) if count > 0]
    for kind in families:
        distinct, repeated, seen = [], [], set()
        for rule in ranked:
            if ("FORMULA" if rule["resultKind"] == "FORMULA" else "CONDITION") != kind:
                continue
            relationship = frozenset(rule_reference_columns(rule))
            (repeated if relationship in seen else distinct).append(rule)
            seen.add(relationship)
        for rule in (distinct + repeated)[:TOP_RULES]:
            presented = _present_rule(rule, labels)
            presented["detail"] = build_rule_detail(rule, rows, analysis["rows"], labels, seed=seed)
            families[kind].append(presented)
    return {"status": "success", "data": {
        "rules": families, "source": "MIXED_PATTERN", "algorithm": analysis["algorithm"],
        "sourceRows": total, "sampleRows": len(rows), **_column_scope(columns, source_columns),
        "sampling": "UNIFORM_RESERVOIR", "sampleSeed": seed, "detectionScope": "ANALYZED_SAMPLE",
        "elapsedSeconds": round(time.monotonic() - started, 2),
        "counts": {kind: sum(("FORMULA" if rule["resultKind"] == "FORMULA" else "CONDITION") == kind for rule in ranked) for kind in families},
        "discoveredCounts": {kind: sum(("FORMULA" if rule["resultKind"] == "FORMULA" else "CONDITION") == kind for rule in analysis["rules"]) for kind in families},
        "violationsOnly": True,
        "formulaStatus": analysis["metrics"].get("continuous", {}).get("status"),
        "topLimit": TOP_RULES, "targetLimit": 24, "formulaTargetLimit": 12,
    }}
