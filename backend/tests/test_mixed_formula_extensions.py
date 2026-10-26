"""Generic formula coverage and violation checks using uploaded string values."""
from decimal import Decimal
import json
import math
import sqlite3
import unittest

import numpy as np
from fastapi import HTTPException

from backend.services.mixed_continuous_algorithm import (
    evaluate_formula_expression, formula_result_accepts, _corr, _ratio_correlations,
)
from backend.services.mixed_formula import compile_expression, evaluate_expression
from backend.services.mixed_pattern_algorithm import evaluate_pattern_predicate
from backend.tests.test_mixed_continuous_algorithm import discover, formula_columns
from backend.tests.mixed_numeric_sqlite import adapt_numeric_text_sql, install_numeric_text_functions


def strings(rows):
    return [{name: format(value, ".17g") if isinstance(value, (float, np.floating)) else str(value)
             for name, value in row.items()} for row in rows]


class MixedFormulaExtensionTests(unittest.TestCase):
    def sqrt_rows(self, count=1600):
        rng = np.random.default_rng(774)
        rows = [{"A": a, "B": b, "Y": 100 * a / math.sqrt(b)}
                for a, b in zip(rng.uniform(20, 700, count), rng.integers(1, 10, count))]
        return strings(rows)

    def test_optional_sqrt_ratio_finds_rule_and_real_violations(self):
        rows = self.sqrt_rows()
        bad = set(range(0, len(rows), 100))
        for index in bad:
            rows[index]["Y"] = str(float(rows[index]["Y"]) + 5000)
        original = json.dumps(rows)
        result = discover(rows, formulaSqrtEnabled=True, maxConditionalGroups=0)
        self.assertEqual(1, len(result["rules"]))
        rule = result["rules"][0]
        self.assertEqual({"A", "B"}, formula_columns(rule["resultPredicate"]["expression"]))
        self.assertIn('"SQRT"', json.dumps(rule["resultPredicate"]))
        self.assertEqual("ROBUST_SQRT_RATIO", rule["validation"]["discoveryMethod"])
        detected = {i for i, row in enumerate(rows) if evaluate_pattern_predicate(rule["predicate"], row)
                    and not formula_result_accepts(rule["resultPredicate"], row)}
        self.assertEqual(bad, detected)
        self.assertEqual(original, json.dumps(rows))
        for value in ("0", "-2", "", None, "wrong"):
            self.assertFalse(evaluate_pattern_predicate(rule["predicate"], {"A": "20", "B": value, "Y": "1"}))
            self.assertIsNone(evaluate_formula_expression(rule["resultPredicate"]["expression"], {"A": "20", "B": value}))
        self.assertIn("B > 0", rule["expression"])
        self.assertTrue(result["metrics"]["ratioSearch"]["sqrtEnabled"])
        json.dumps(result, allow_nan=False)

    def test_sqrt_is_opt_in_and_validation_cannot_refit(self):
        rows = self.sqrt_rows()
        self.assertEqual([], discover(rows, maxConditionalGroups=0)["rules"])
        self.assertEqual([], discover(rows, formulaSqrtEnabled=True, maxFormulaFeatures=1, maxConditionalGroups=0)["rules"])
        for index in np.random.default_rng(42).permutation(len(rows))[:400]:
            rows[int(index)]["Y"] = str(float(rows[int(index)]["Y"]) + 5000)
        self.assertEqual([], discover(rows, formulaSqrtEnabled=True, maxConditionalGroups=0)["rules"])
        with self.assertRaises(ValueError):
            discover(rows, formulaSqrtEnabled="true")

    def test_ratio_denominator_need_not_be_marginally_correlated(self):
        rng = np.random.default_rng(778)
        rows = []
        for a, b in zip(rng.uniform(-100, 100, 1800), rng.uniform(1, 30, 1800)):
            rows.append({"A": a, "B": b, "Y": a / b,
                         **{f"PROXY_{j}": a + rng.normal(0, 25) for j in range(8)}})
        result = discover(strings(rows), maxConditionalGroups=0)
        self.assertEqual(1, len(result["rules"]))
        rule = result["rules"][0]
        self.assertEqual({"A", "B"}, formula_columns(rule["resultPredicate"]["expression"]))
        self.assertEqual("ROBUST_RATIO", rule["validation"]["discoveryMethod"])
        self.assertEqual(1, rule["validation"]["confidence"])

    def test_six_term_sum_beats_correlated_proxy_and_keeps_option_bound(self):
        rng = np.random.default_rng(841)
        rows = []
        for values in rng.uniform(10, 100, (1500, 6)):
            total = float(values.sum())
            rows.append({**{f"X{j}": value for j, value in enumerate(values)}, "Y": total,
                         "PROXY": total + rng.normal(0, 1)})
        rows = strings(rows)
        result = discover(rows, maxFormulaFeatures=6, maxConditionalGroups=0)
        rule = result["rules"][0]
        self.assertEqual({f"X{j}" for j in range(6)}, formula_columns(rule["resultPredicate"]["expression"]))
        self.assertEqual(6, rule["formulaComplexity"])
        self.assertEqual(1, rule["validation"]["confidence"])
        self.assertTrue(all(formula_result_accepts(rule["resultPredicate"], row) for row in rows))
        narrower = discover(rows, maxFormulaFeatures=3, maxConditionalGroups=0)
        self.assertTrue(all(item["formulaComplexity"] <= 3 for item in narrower["rules"]))
        self.assertEqual(8, discover(rows, maxFormulaFeatures=8, maxConditionalGroups=0)["metrics"]["unitSearch"]["maxTerms"])
        with self.assertRaises(ValueError):
            discover(rows, maxFormulaFeatures=9)

    def test_optional_transforms_do_not_publish_unrelated_data(self):
        rng = np.random.default_rng(961)
        rows = strings([{f"X{j}": value for j, value in enumerate(values)} | {"Y": y}
                        for values, y in zip(rng.uniform(1, 20, (1200, 8)), rng.normal(10, 3, 1200))])
        self.assertEqual([], discover(rows, formulaSqrtEnabled=True, maxFormulaFeatures=8, maxConditionalGroups=0)["rules"])

    def test_batched_ratio_ranking_keeps_pairwise_missing_and_clipping_semantics(self):
        rng = np.random.default_rng(741)
        values = rng.normal(size=(256, 40)) * (10. ** rng.uniform(-12, 12, 40))
        target = rng.normal(size=256)
        values[:, 0] = 2
        values[0, 1] = np.nan
        values[2:15, 2] = np.inf
        values[5, 3] = 1e30
        for actual in (target, np.where(np.arange(256) % 31, target, np.nan)):
            np.testing.assert_allclose(_ratio_correlations(values, actual),
                [_corr(values[:, index], actual) for index in range(values.shape[1])], rtol=1e-11, atol=1e-13)

    def test_eight_term_identity_compiles_with_existing_ast_limits(self):
        rng = np.random.default_rng(815)
        rows = strings([{**{f"X{j}": value for j, value in enumerate(values)}, "Y": float(values.sum())}
                        for values in rng.uniform(1, 20, (1000, 8))])
        result = discover(rows, maxFormulaFeatures=8, maxConditionalGroups=0)
        self.assertEqual(1, len(result["rules"]))
        rule = result["rules"][0]
        self.assertEqual({f"X{j}" for j in range(8)}, formula_columns(rule["resultPredicate"]["expression"]))
        metadata = [{"COLUMN_NAME": name, "DATA_TYPE": "VARCHAR2"} for name in rows[0]]
        _, _, referenced = compile_expression(rule["resultPredicate"]["expression"], metadata, forbidden_column="Y")
        self.assertEqual({f"X{j}" for j in range(8)}, referenced)

    def test_sqrt_ast_python_sql_parity_and_validation(self):
        expression = {"operator": "DIVIDE", "left": {"column": "A", "numericText": True},
                      "right": {"operator": "SQRT", "operand": {"column": "B", "numericText": True}}}
        columns = [{"COLUMN_NAME": name, "DATA_TYPE": "VARCHAR2"} for name in ("A", "B", "Y")]
        sql, binds, referenced = compile_expression(expression, columns, forbidden_column="Y")
        self.assertEqual({"A", "B"}, referenced)
        self.assertIn("SQRT(CASE WHEN", sql)
        with sqlite3.connect(":memory:") as conn:
            install_numeric_text_functions(conn)
            conn.create_function("SQRT", 1, lambda value: None if value is None else math.sqrt(value))
            conn.execute("CREATE TABLE INPUTS (A TEXT, B TEXT)")
            for a, b, expected in (("12", "4", 6), ("0", "4", 0), ("12", "0", None),
                                   ("12", "-4", None), ("12", "bad", None), ("12", None, None),
                                   (None, "4", None), ("bad", "4", None), ("12", "02", None)):
                with self.subTest(a=a, b=b):
                    conn.execute("DELETE FROM INPUTS")
                    conn.execute("INSERT INTO INPUTS VALUES (?, ?)", (a, b))
                    actual = conn.execute("SELECT " + adapt_numeric_text_sql(sql) + " FROM INPUTS T", binds).fetchone()[0]
                    self.assertEqual(expected, actual)
                    self.assertEqual(expected, evaluate_expression(expression, {"A": a, "B": b}))
                    self.assertEqual(expected, evaluate_formula_expression(expression, {"A": a, "B": b}))
        # Domain guards are inside SQRT, so an optimizer need not evaluate IF first.
        root = {"operator": "SQRT", "operand": {"column": "A", "numericText": True}}
        self.assertEqual(Decimal(0), evaluate_expression(root, {"A": "0"}))
        for bad in ({"operator": "SQRT", "operand": {"column": "Y", "numericText": True}},
                    {"operator": "SQRT", "operand": {"column": "A", "numericText": True}, "sql": "BAD"},
                    {"operator": "SQRT", "left": {"column": "A", "numericText": True}},
                    {"operator": "SQRT", "operand": {"value": 4}}):
            with self.subTest(bad=bad), self.assertRaises(HTTPException):
                compile_expression(bad, columns, forbidden_column="Y")
        oversized = {"column": "A", "numericText": True}
        for _ in range(10):
            oversized = {"operator": "SQRT", "operand": oversized}
        with self.assertRaises(HTTPException) as expanded:
            compile_expression(oversized, columns)
        self.assertIn("size limit", expanded.exception.detail)
        oversized = {"column": "A", "numericText": True}
        for _ in range(14):
            oversized = {"operator": "SQRT", "operand": oversized}
        with self.assertRaises(HTTPException):
            compile_expression(oversized, columns)

    def test_saved_sqrt_rule_detects_source_violations_and_rechecks_final_edit(self):
        from backend.services import mixed_pattern_service as patterns, mixed_xai_service as xai
        from backend.services import edit_work_service as editing
        from backend.tests.test_mixed_continuous_pipeline import UploadedNumericConnection
        from backend.tests.test_mixed_pattern_service import PAYLOAD
        from backend.tests.test_xai_sql_compatibility import sqlite_statement

        source = self.sqrt_rows(800)
        corrupted = set(range(0, len(source), 100))
        for index in corrupted:
            source[index]["Y"] = str(float(source[index]["Y"]) + 5000)
        rows = [("A", "001", index + 1, row["A"], row["B"], row["Y"]) for index, row in enumerate(source)]
        conn = UploadedNumericConnection(rows, numeric_columns=("A", "B", "Y"))
        self.addCleanup(conn.db.close)
        conn.db.create_function("SQRT", 1, lambda value: None if value is None else math.sqrt(value))
        discovery = xai.discover(conn, {**PAYLOAD, "targetColumns": ["Y"], "formulaSqrtEnabled": True})
        self.assertEqual(1, discovery["formulaRuleCount"])
        stored = next(rule for rule in conn.records(patterns.RULE_TABLE) if rule["RESULT_KIND"] == "FORMULA")
        saved_ast, saved_validation = stored["RESULT_JSON"], stored["VALIDATION_JSON"]
        conn.db.executemany("INSERT INTO SOURCE_UPLOADED VALUES (?, ?, ?, ?, ?, ?)", [
            ("A", "001", 801, "12", "4", "bad"), ("A", "001", 802, "12", "4", None),
            ("A", "001", 803, "12", "0", "600"), ("A", "001", 804, "12", "-4", "600"),
            ("A", "001", 805, "12", "invalid", "600"), ("A", "001", 806, "12", "4", "600")])
        detected = xai.detect(conn, {**PAYLOAD, "maxViolationRows": 1000})
        self.assertEqual(len(corrupted) + 2, detected["violationCount"])
        violations = conn.records(patterns.VIOLATION_TABLE)
        expected_ids = {str(index + 1) for index in corrupted} | {"801", "802"}
        self.assertEqual(expected_ids, {row["CASE_ID"] for row in violations})
        refreshed = next(rule for rule in conn.records(patterns.RULE_TABLE) if rule["RULE_ID"] == stored["RULE_ID"])
        self.assertEqual(saved_ast, refreshed["RESULT_JSON"])
        self.assertEqual(saved_validation, refreshed["VALIDATION_JSON"])

        columns = {name: {"COLUMN_NAME": name, "DATA_TYPE": "NUMBER" if name == "FILE_ROW_NO" else "VARCHAR2"}
                   for name in ("A", "B", "Y", "FILE_ROW_NO", editing.TRACKING_COLUMN)}
        reviewed = {**stored, "EDIT_RULE_ID": 1, "SOURCE_RULE_TYPE": "ASSOCIATION", "USER_RULE_YN": "N",
                    "SOURCE_OBJECT_NAME": stored["MODEL_NAME"], "SOURCE_RULE_ID": stored["RULE_ID"],
                    "TARGET_COLUMN": "Y", "CASE_ID_COLUMN": "FILE_ROW_NO",
                    "CONDITION_AST": json.loads(stored["CONDITION_JSON"]), "RESULT_AST": json.loads(saved_ast)}
        sql, binds = editing._build_live_rule_violation_sql(None, reviewed, None, table_columns_override=columns)
        adapted = adapt_numeric_text_sql(sqlite_statement(sql)).replace('"APP_OWNER"."SOURCE_DATA"', "SOURCE_UPLOADED")
        cursor = conn.db.execute(adapted, {key: float(value) if isinstance(value, Decimal) else value for key, value in binds.items()})
        live = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
        self.assertEqual(expected_ids, {row["CASE_ID"] for row in live})
        self.assertEqual(["A", "B"], reviewed["FEATURE_COLUMNS"])

        conn.db.execute("ATTACH DATABASE ':memory:' AS EDIT_OWNER")
        conn.db.execute('CREATE TABLE EDIT_OWNER.EDIT_SOURCE (A TEXT, B TEXT, Y TEXT, "INIT$_SOURCE_ROWID" TEXT)')
        conn.db.execute("INSERT INTO EDIT_OWNER.EDIT_SOURCE VALUES ('12', '4', '620', 'EDIT1')")

        class EditingCursor:
            def execute(self, statement, parameters):
                self.cursor = conn.db.execute(adapt_numeric_text_sql(statement),
                    {key: float(value) if isinstance(value, Decimal) else value for key, value in parameters.items()})
            def fetchone(self):
                return self.cursor.fetchone()

        cursor = EditingCursor()
        self.assertEqual("600.0", editing._validate_pattern_replacement(cursor, reviewed, "600", columns,
            owner="EDIT_OWNER", edit_table="EDIT_SOURCE", source_rowid="EDIT1"))
        with self.assertRaises(HTTPException):
            editing._validate_pattern_replacement(cursor, reviewed, "620", columns,
                owner="EDIT_OWNER", edit_table="EDIT_SOURCE", source_rowid="EDIT1")
        conn.db.execute("UPDATE EDIT_OWNER.EDIT_SOURCE SET B='9'")
        with self.assertRaises(HTTPException):
            editing._validate_pattern_replacement(cursor, reviewed, "600", columns,
                owner="EDIT_OWNER", edit_table="EDIT_SOURCE", source_rowid="EDIT1")
        self.assertEqual("400.0", editing._validate_pattern_replacement(cursor, reviewed, "400", columns,
            owner="EDIT_OWNER", edit_table="EDIT_SOURCE", source_rowid="EDIT1"))
        conn.db.execute("UPDATE EDIT_OWNER.EDIT_SOURCE SET B='-1'")
        with self.assertRaises(HTTPException) as invalid:
            editing._validate_pattern_replacement(cursor, reviewed, "400", columns,
                owner="EDIT_OWNER", edit_table="EDIT_SOURCE", source_rowid="EDIT1")
        self.assertEqual(409, invalid.exception.status_code)


if __name__ == "__main__":
    unittest.main()
