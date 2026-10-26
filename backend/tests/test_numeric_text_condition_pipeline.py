"""Uploaded strings -> condition discovery -> full-source SQL -> final review.

SQLite executes the generated predicates with the existing Oracle scalar adapter.
This verifies source/AST contracts, not Oracle execution plans or NLS behavior.
"""
import copy
import json
import unittest
from decimal import Decimal

import numpy as np

from backend.services import edit_work_service as editing
from backend.services import mixed_pattern_service as patterns
from backend.services import mixed_xai_service as xai
from backend.services.mixed_pattern_algorithm import evaluate_pattern_predicate
from backend.tests.mixed_numeric_sqlite import adapt_numeric_text_sql
from backend.tests.test_mixed_continuous_pipeline import UploadedNumericConnection
from backend.tests.test_mixed_pattern_service import PAYLOAD
from backend.tests.test_xai_sql_compatibility import sqlite_statement


NAMES = ("GROUP_CODE", "REGION", "FILE_ROW_NO", "X", "Y")
COLUMNS = {name: {"COLUMN_NAME": name, "DATA_TYPE": "NUMBER" if name == "FILE_ROW_NO" else "VARCHAR2"}
           for name in NAMES}


class NumericTextConditionPipelineTests(unittest.TestCase):
    def test_uploaded_ranges_and_labels_detect_later_errors_without_refitting(self):
        rng = np.random.default_rng(704)
        rows = []
        for index, value in enumerate(rng.integers(0, 100, 1600)):
            rows.append(("LOW" if value < 50 else "HIGH", "001", index + 1,
                         str(value), str(10 * value + 2)))
        conn = UploadedNumericConnection(rows)
        self.addCleanup(conn.db.close)
        result = xai.discover(conn, {**PAYLOAD, "targetColumns": ["GROUP_CODE", "Y"],
                                    "continuousEnabled": False})
        self.assertEqual(0, result["formulaRuleCount"])
        inferred = {item["column"] for item in result["encoding"]["numericTextInference"]}
        self.assertEqual({"X", "Y"}, inferred)
        self.assertNotIn("REGION", inferred)
        stored = conn.records(patterns.RULE_TABLE)
        self.assertTrue({"VALUE", "RANGE"} <= {rule["RESULT_KIND"] for rule in stored})
        original = [dict(zip(NAMES, row)) for row in rows]
        snapshots = {rule["RULE_ID"]: (rule["CONDITION_JSON"], rule["RESULT_JSON"], rule["VALIDATION_JSON"])
                     for rule in stored}
        validation = np.random.default_rng(42).permutation(len(rows))[:len(rows) // 4]
        for rule in stored:
            condition, consequence = json.loads(rule["CONDITION_JSON"]), json.loads(rule["RESULT_JSON"])
            profile = json.loads(rule["VALIDATION_JSON"])
            applicable = [original[int(index)] for index in validation
                          if evaluate_pattern_predicate(condition, original[int(index)])]
            matched = sum(evaluate_pattern_predicate(consequence, row) for row in applicable)
            self.assertEqual(len(applicable), profile["conditionCount"])
            self.assertEqual(matched, profile["supportCount"])
            self.assertNotIn(rule["RESULT_COLUMN"], {atom["column"] for atom in xai._atomic_nodes(condition)})
            if rule["RESULT_KIND"] == "RANGE":
                self.assertTrue(all(atom.get("numericText") and atom["valueType"] == "NUMBER"
                                    for atom in xai._atomic_nodes(consequence)))

        appended = []
        for kind in ("VALUE", "RANGE"):
            rule = next(rule for rule in stored if rule["RESULT_KIND"] == kind)
            condition, consequence = json.loads(rule["CONDITION_JSON"]), json.loads(rule["RESULT_JSON"])
            source = next(row for row in original if evaluate_pattern_predicate(condition, row)
                          and evaluate_pattern_predicate(consequence, row))
            bad_values = ["WRONG_LABEL"] if kind == "VALUE" else [
                next(value for value in ("-10000", "10000")
                     if not evaluate_pattern_predicate(consequence, {**source, "Y": value})),
                "not numeric", None, "01"]
            for value in bad_values:
                appended.append({**source, rule["RESULT_COLUMN"]: value,
                                 "FILE_ROW_NO": len(rows) + len(appended) + 1})
        conn.db.executemany("INSERT INTO SOURCE_UPLOADED VALUES (?, ?, ?, ?, ?)",
                            [tuple(row[name] for name in NAMES) for row in appended])
        before_detection = copy.deepcopy(conn.records(patterns.RULE_TABLE))
        detected = xai.detect(conn, {**PAYLOAD, "maxViolationRows": 1000})
        self.assertEqual("FULL_TARGET", detected["metricsCohort"])
        self.assertEqual(len(rows) + len(appended), detected["evaluatedRows"])
        all_rows = original + appended
        violations = conn.records(patterns.VIOLATION_TABLE)
        all_expected = set()
        for number, rule in enumerate(before_detection, start=1):
            condition, consequence = json.loads(rule["CONDITION_JSON"]), json.loads(rule["RESULT_JSON"])
            expected = {str(row["FILE_ROW_NO"]) for row in all_rows
                        if evaluate_pattern_predicate(condition, row)
                        and not evaluate_pattern_predicate(consequence, row)}
            actual = {row["CASE_ID"] for row in violations if row["RULE_ID"] == rule["RULE_ID"]}
            self.assertEqual(expected, actual)
            all_expected.update(expected)
            reviewed = {**rule, "EDIT_RULE_ID": number, "SOURCE_RULE_TYPE": "ASSOCIATION", "USER_RULE_YN": "N",
                        "SOURCE_OBJECT_NAME": rule["MODEL_NAME"], "SOURCE_RULE_ID": rule["RULE_ID"],
                        "TARGET_COLUMN": rule["RESULT_COLUMN"], "CASE_ID_COLUMN": "FILE_ROW_NO",
                        "CONDITION_AST": condition, "RESULT_AST": consequence}
            sql, binds = editing._build_live_rule_violation_sql(None, reviewed, None, table_columns_override=COLUMNS)
            adapted = adapt_numeric_text_sql(sqlite_statement(sql)).replace('"APP_OWNER"."SOURCE_DATA"', "SOURCE_UPLOADED")
            cursor = conn.db.execute(adapted, {key: float(value) if isinstance(value, Decimal) else value
                                               for key, value in binds.items()})
            live = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
            self.assertEqual(expected, {str(row["CASE_ID"]) for row in live})
            for row in appended:
                self.assertEqual(evaluate_pattern_predicate(consequence, row),
                                 editing._pattern_result_accepts_value(reviewed, row[rule["RESULT_COLUMN"]]))
        self.assertTrue({str(row["FILE_ROW_NO"]) for row in appended} <= all_expected)
        self.assertEqual(len(all_expected), detected["uniqueViolationCount"])
        for rule in conn.records(patterns.RULE_TABLE):
            self.assertEqual(snapshots[rule["RULE_ID"]],
                             (rule["CONDITION_JSON"], rule["RESULT_JSON"], rule["VALIDATION_JSON"]))
        self.assertEqual(0, conn.commits)

    def test_numeric_target_boundaries_use_decimal_and_strict_source_policy(self):
        predicate = {"column": "Y", "operator": ">", "value": "16777216.1",
                     "valueType": "NUMBER", "numericText": True}
        reviewed = {"TARGET_COLUMN": "Y", "RESULT_AST": predicate}
        for value, accepted in (("16777216.2", True), ("16777216.1", False),
                                (" 16777216.2 ", True), ("016777216.2", False),
                                ("16,777,216.2", False), ("NaN", False), (None, False)):
            with self.subTest(value=value):
                self.assertIs(accepted, evaluate_pattern_predicate(predicate, {"Y": value}))
                self.assertIs(accepted, editing._pattern_result_accepts_value(reviewed, value))
        sql, binds = xai.compile_predicate(predicate, list(COLUMNS.values()))
        self.assertNotIn("BINARY_FLOAT", sql)
        self.assertEqual([Decimal("16777216.1")], list(binds.values()))
        branch = {**predicate, "operator": "<=", "value": 16777216, "valueType": "BINARY_FLOAT"}
        self.assertTrue(evaluate_pattern_predicate(branch, {"Y": "16777217"}))
        branch_sql, _ = xai.compile_predicate(branch, list(COLUMNS.values()))
        self.assertIn(" AS BINARY_FLOAT)", branch_sql)


if __name__ == "__main__":
    unittest.main()
