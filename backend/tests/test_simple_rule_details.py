import copy
import unittest
from unittest.mock import patch

from backend.services import simple_rule_details as detail


class RuleDetailTests(unittest.TestCase):
    def formula(self):
        return {"resultKind":"FORMULA", "resultColumn":"TOTAL", "predicate":{"operator":"NOT_NULL","column":"A","numericText":True},
                "resultPredicate":{"operator":"WITHIN_TOLERANCE","column":"TOTAL","numericText":True,
                    "expression":{"operator":"ADD","left":{"column":"A","numericText":True},"right":{"column":"B","numericText":True}},
                    "absoluteTolerance":.01,"relativeTolerance":0}}

    def test_frozen_formula_detects_training_violations_and_keeps_validation_separate(self):
        rule = self.formula(); before = copy.deepcopy(rule)
        rows = [{"A":"1000","B":"10","TOTAL":"1010","__source_row__":15},
                {"A":"1000","B":"10","TOTAL":"1050","__source_row__":20},
                {"A":"1000","B":"10","TOTAL":"bad","__source_row__":30},
                {"A":"","B":"10","TOTAL":"10"}, {"A":"1","B":"1","TOTAL":"bad","__source_row__":40}]
        partitions = [{"rowIndex":i,"partition":"TRAIN" if i == 4 else "VALIDATION"} for i in range(5)]
        result = detail.build_rule_detail(rule, rows, partitions, {"A":"금액","B":"추가","TOTAL":"합계"}, seed=17)
        self.assertEqual(result["cohort"], "ANALYZED_SAMPLE")
        self.assertEqual(result["scannedRows"], 5)
        self.assertEqual(result["validationCohort"], "SELECTION_VALIDATION")
        self.assertEqual(result["stats"], {"applied":4,"matched":1,"different":3,"unscorable":2})
        self.assertEqual(detail.count_rule_violations(rule, rows), result["stats"]["different"])
        self.assertEqual(result["validationStats"], {"applied":3,"matched":1,"different":2,"unscorable":1})
        self.assertEqual([row["sourceRow"] for row in result["rows"]], [15,20,30,40])
        self.assertEqual(result["rows"][0]["expected"], 1010)
        self.assertEqual(result["rows"][1]["residual"], 40)
        self.assertIsNone(result["rows"][2]["actual"])
        self.assertEqual(rule, before)

    def test_conditional_training_violations_are_detected_with_bounded_display(self):
        rule = {"resultKind":"VALUE","resultColumn":"RESULT","predicate":{"operator":"=","column":"GROUP","value":"VIP"},
                "resultPredicate":{"operator":"=","column":"RESULT","value":"FREE"}}
        rows = [{"GROUP":"VIP","RESULT":"PAID" if i < 5 else "FREE","__source_row__":i + 100} for i in range(260)]
        partitions = [{"rowIndex":i,"partition":"TRAIN" if i < 5 else "VALIDATION"} for i in range(260)]
        result = detail.build_rule_detail(rule, rows, partitions, {"GROUP":"그룹","RESULT":"배송"}, seed=9)
        self.assertEqual(result["stats"]["applied"], 260)
        self.assertEqual(result["stats"]["matched"], 255)
        self.assertEqual(result["validationStats"]["different"], 0)
        self.assertEqual(result["validationStats"]["applied"], 255)
        self.assertEqual(len(result["rows"]), 120)
        self.assertEqual(sum(row["status"] != "MATCH" for row in result["rows"]), 5)
        self.assertTrue(all(row["expected"] is None for row in result["rows"]))

    def test_long_values_and_response_bytes_are_bounded_without_changing_counts(self):
        rule = {"resultKind":"VALUE","resultColumn":"RESULT","predicate":{"operator":"NOT_NULL","column":"GROUP"},
                "resultPredicate":{"operator":"=","column":"RESULT","value":"Y"}}
        rows = [{"GROUP":"가" * 2000,"RESULT":"Y"} for _ in range(200)]
        partitions = [{"rowIndex":i,"partition":"VALIDATION"} for i in range(200)]
        with patch.object(detail,"MAX_DETAIL_BYTES",2000):
            result = detail.build_rule_detail(rule, rows, partitions, {"GROUP":"그룹","RESULT":"결과"}, seed=0)
        self.assertLess(result["shownRows"], 120)
        self.assertTrue(result["truncatedCells"])
        self.assertEqual(result["stats"]["applied"], 200)
        self.assertTrue(all(len(row["values"]["GROUP"]) == 160 for row in result["rows"]))
