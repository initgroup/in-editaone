"""Read-only Quick Editing history presented as bounded key-rule summaries."""
import math

from fastapi import HTTPException

from backend.services import flow_work_service as flows
from backend.services.editing_result_service import read_results
from backend.services.mixed_xai_service import _json_object
from backend.services.simple_editing import _present_rule
from backend.services.simple_rule_details import rule_reference_columns, _number


def _authorized_run(conn, run_id, user_id, include_all_users):
    history = flows.list_quick_edit_history(conn, "M04001", user_id, include_all_users, 1, 1, flow_run_id=run_id)
    if not history.get("data"):
        raise HTTPException(404, "Quick Editing execution history was not found.")
    run = history["data"][0]
    nodes = flows.list_node_run_history(conn, run_id).get("data") or []
    detail = flows.build_quick_edit_history_detail(run, nodes)
    state = detail["restoreState"]
    if not state.get("tableOwner") or not state.get("tableName"):
        raise HTTPException(409, "이 실행의 원본 대상 정보가 없어 결과를 조회할 수 없습니다.")
    return run, state


def _count(value):
    return None if value is None else int(value)


def _finite(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def present_stored_rule(entry):
    row = entry["row"]
    predicate = _json_object(row.get("CONDITION_AST") or row.get("CONDITION_JSON"), "CONDITION_JSON")
    consequent = _json_object(row.get("RESULT_AST") or row.get("RESULT_JSON"), "RESULT_JSON")
    rule = {"ruleId": entry["key"], "resultKind": row["RESULT_KIND"], "resultColumn": row["RESULT_COLUMN"],
            "predicate": predicate, "resultPredicate": consequent, "validation": {"confidence": row.get("VALIDATION_CONFIDENCE"), "conditionCount": row.get("VALIDATION_COUNT") or 0}}
    comments = entry.get("columnComments") or {}
    labels = {name: comments.get(name) or name for name in rule_reference_columns(rule)}
    result = _present_rule(rule, labels)
    different = _count(row.get("VIOLATION_COUNT"))
    applied, matched = _count(row.get("CONDITION_TOTAL_COUNT")), _count(row.get("SUPPORT_COUNT"))
    consistent = applied is not None and matched is not None and different is not None and applied - matched == different
    if not consistent:
        applied = matched = None
    result.update(storedRuleKey=entry["key"], detail={
        "cohort": "STORED_DETECTION", "stats": {"different": different, "applied": applied, "matched": matched},
        "countConsistency": "RECORDED" if consistent else "UNAVAILABLE_OR_INCONSISTENT",
        "target": {"key": rule["resultColumn"], "label": labels[rule["resultColumn"]]},
        "inputs": [], "rows": [], "shownRows": 0, "rowLimit": 100, "loaded": False})
    return result


def read_history_result(conn, run_id, user_id, include_all_users=False, rule_key=""):
    run, state = _authorized_run(conn, run_id, user_id, include_all_users)
    scope = dict(target_owner=state["tableOwner"], target_table=state["tableName"], include_all_users=include_all_users)
    if rule_key:
        data = read_results(conn, run_id, user_id, **scope, view="violations", rule_key=rule_key, page_size=100)["data"]
        if data["rule"]["source"] != "MIXED_PATTERN":
            raise HTTPException(400, "Only stored mixed-pattern rules are supported.")
        result = present_stored_rule(data["rule"])
        consequent = _json_object(data["rule"]["row"].get("RESULT_AST") or data["rule"]["row"].get("RESULT_JSON"), "RESULT_JSON")
        records = []
        for index, item in enumerate(data["violations"]):
            actual = _number(item.get("ACTUAL_VALUE"), consequent.get("numericText", False)) if item.get("ACTUAL_NUMERIC_VALID_YN") != "N" else None
            expected = _finite(item.get("EXPECTED_VALUE"))
            residual = _finite(item.get("RESIDUAL"))
            records.append({"id": index, "sourceRow": str(item.get("CASE_ID") or item.get("VIOLATION_ID") or "")[:160],
                            "status": "UNSCORABLE" if result["kind"] == "FORMULA" and (expected is None or actual is None) else "DIFFERENT",
                            "values": {result["detail"]["target"]["key"]: str(item.get("ACTUAL_VALUE") if item.get("ACTUAL_VALUE") is not None else "")[:160]},
                            "expected": expected, "actual": actual, "residual": residual, "truncated": False})
        result["detail"].update(rows=records, shownRows=len(records), savedRows=data["total"], loaded=True)
        return {"status": "success", "data": result}
    families, counts, discovered = {}, {}, {}
    warnings = []
    for family in ("FORMULA", "CONDITION"):
        data = read_results(conn, run_id, user_id, **scope, family=family, source="MIXED_PATTERN", page_size=5, violations_only=True)["data"]
        families[family] = [present_stored_rule(entry) for entry in data["rules"]]
        counts[family] = data["total"]
        sources = [item for item in data["summary"]["sourceCounts"] if item["family"] == family and item["source"] == "MIXED_PATTERN"]
        discovered[family] = sum(item.get("discoveredRuleCount", 0) for item in sources)
        warnings.extend(data["diagnostics"].get("warnings", []))
    return {"status": "success", "data": {"rules": families, "counts": counts, "discoveredCounts": discovered,
        "source": "MIXED_PATTERN", "detectionScope": "STORED_TARGET", "violationsOnly": True,
        "history": {"flowRunId": run_id, "status": run.get("STATUS"), "startedAt": run.get("STARTED_AT"),
                    "project": state.get("projectName") or state.get("projectCode"),
                    "scenario": state.get("scenarioName") or state.get("scenarioCode"),
                    "targetOwner": state["tableOwner"], "targetTable": state["tableName"]},
        "warnings": warnings, "topLimit": 5}}
