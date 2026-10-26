"""Uploaded numeric measurements keep range semantics without converting codes."""
import copy
import json
import unittest
from decimal import Decimal

import numpy as np

from backend.services.mixed_pattern_algorithm import analyze_pattern_rows, evaluate_pattern_predicate
from backend.services.mixed_pattern_encoding import condition_numeric_views
from backend.services.mixed_xai_service import compile_predicate
from backend.services.edit_work_service import _pattern_result_accepts_value


class NumericTextConditionTests(unittest.TestCase):
    def test_uploaded_measurement_ranges_find_label_violations_with_exact_counts(self):
        rng = np.random.default_rng(246)
        values = rng.integers(1, 101, 2400)
        corrupt = set(range(0, len(values), 150))
        rows = [{"MEASURE": str(value), "LABEL": str((value - 1) // 25)} for value in values]
        for index in corrupt:
            rows[index]["LABEL"] = "wrong"
        before = copy.deepcopy(rows)
        columns = [{"name": name, "dataType": "VARCHAR2"} for name in rows[0]]
        analysis = analyze_pattern_rows(rows, columns, {
            "targetColumns": ["LABEL"], "continuousEnabled": False, "minConfidence": .95})
        self.assertEqual(rows, before)
        self.assertEqual(len(analysis["rules"]), 4)
        self.assertEqual([entry["column"] for entry in analysis["encoding"]["numericTextInference"]], ["MEASURE"])
        found = set()
        for rule in analysis["rules"]:
            self.assertIn('"numericText": true', json.dumps(rule["predicate"]))
            self.assertNotIn('"LABEL"', json.dumps(rule["predicate"]))
            sql, _ = compile_predicate(rule["predicate"], [{"COLUMN_NAME": name, "DATA_TYPE": "VARCHAR2"} for name in rows[0]])
            self.assertIn("JSON_VALUE", sql)
            self.assertIn("AS BINARY_FLOAT)", sql)
            for cohort, metrics in (("TRAIN", rule), ("VALIDATION", rule["validation"])):
                selected = [rows[item["rowIndex"]] for item in analysis["rows"] if item["partition"] == cohort]
                applicable = [row for row in selected if evaluate_pattern_predicate(rule["predicate"], row)]
                matching = [row for row in applicable if evaluate_pattern_predicate(rule["resultPredicate"], row)]
                self.assertEqual(metrics["conditionCount"], len(applicable))
                self.assertEqual(metrics["supportCount"], len(matching))
            found.update(index for index, row in enumerate(rows)
                         if evaluate_pattern_predicate(rule["predicate"], row)
                         and not evaluate_pattern_predicate(rule["resultPredicate"], row))
        self.assertEqual(found, corrupt)

    def test_inference_is_train_only_and_preserves_codes_and_strict_invalids(self):
        rows = [{"X": str(i % 70 + 1), "CODE": f"{i % 70 + 1:03}", "LOW": str(i % 3),
                 "TEXT": "word"} for i in range(160)]
        rows[159].update(X="01", TEXT="123")
        columns = [{"name": name, "dataType": "VARCHAR2"} for name in rows[0]]
        target, feature, metadata, inferred, diagnostics = condition_numeric_views(
            rows, columns, np.arange(120), category_limit=32, excluded=set())
        self.assertEqual(inferred, {"X"})
        self.assertIsNone(target[159]["X"])
        self.assertIsNone(feature[159]["X"])
        self.assertEqual(rows[159]["X"], "01")
        self.assertEqual(diagnostics[0]["nonNullCount"], 120)
        self.assertEqual(diagnostics[0]["invalidCount"], 0)
        self.assertEqual([col["dataType"] for col in metadata], ["NUMBER", "VARCHAR2", "VARCHAR2", "VARCHAR2"])
        # A larger existing category budget intentionally retains equality mode.
        self.assertFalse(condition_numeric_views(rows, columns, np.arange(120), category_limit=128, excluded=set())[3])

    def test_float32_boundary_agrees_with_tree_for_original_numeric_text(self):
        boundary = float(np.float32(1))
        predicate = {"column": "X", "operator": "<=", "value": boundary,
                     "valueType": "BINARY_FLOAT", "numericText": True}
        for value in ("1", "1.00000001", "1.00000007", "-1e100", "1e100", "bad", "", "01"):
            with self.subTest(value=value), np.errstate(over="ignore"):
                expected = bool(np.float32(value) <= boundary) if value not in {"bad", "", "01"} else False
                self.assertEqual(evaluate_pattern_predicate(predicate, {"X": value}), expected)

    def test_numeric_text_target_ranges_keep_decimal_precision_and_final_edit_policy(self):
        rule = {"RESULT_COLUMN": "X", "RESULT_AST": {"operator": "AND", "conditions": [
            {"column": "X", "operator": ">", "value": "1.000000000000000000001", "valueType": "NUMBER", "numericText": True},
            {"column": "X", "operator": "<=", "value": 2, "valueType": "NUMBER", "numericText": True}]}}
        for value, expected in (("1.000000000000000000002", True), ("1.000000000000000000001", False),
                                ("2", True), ("02", False), ("2,0", False), ("NaN", False), ("", False)):
            with self.subTest(value=value):
                self.assertEqual(evaluate_pattern_predicate(rule["RESULT_AST"], {"X": value}), expected)
                self.assertEqual(_pattern_result_accepts_value(rule, value), expected)
        rng = np.random.default_rng(8)
        values = rng.uniform(1, 100, 2400)
        rows = [{"X": str(value), "Y": str(value * 2)} for value in values]
        result = analyze_pattern_rows(rows, [{"name": name, "dataType": "VARCHAR2"} for name in ("X", "Y")],
                                      {"targetColumns": ["Y"], "continuousEnabled": False, "targetBins": 4})
        self.assertTrue(result["rules"])
        for item in result["rules"]:
            self.assertEqual(item["resultKind"], "RANGE")
            self.assertIn('"numericText": true', json.dumps(item["resultPredicate"]))
            self.assertNotIn("BINARY_FLOAT", json.dumps(item["resultPredicate"]))
        json.dumps(result, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
