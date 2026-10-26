"""CPU 발굴 로직의 재현성 테스트: python -m unittest -v test_rule_miner.py"""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from cpu_minimal_example import check_file, evaluate_record
from rule_miner import (Settings, mine_tax_brackets, optimal_categorical_intervals,
                        read_csv, run, split_indices)


ROOT = Path(__file__).parent
SAMPLE = ROOT / "data" / "국가통계_가구생활조사_샘플.csv"


class CpuRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = read_csv(SAMPLE)

    def test_input_shape(self):
        self.assertEqual(self.df.shape, (1500, 55))

    def test_cpu_segmentation_boundaries(self):
        x = np.repeat(np.arange(20, 75), 4).astype(float)
        y = np.array(["20대 이하" if v < 30 else "30대" if v < 40 else
                      "40대" if v < 50 else "50대" if v < 60 else
                      "60대" if v < 70 else "70대 이상" for v in x])
        cuts, categories = optimal_categorical_intervals(x, y, np.ones(len(x), dtype=bool), 6)
        self.assertEqual(cuts, [29.5, 39.5, 49.5, 59.5, 69.5])
        self.assertEqual(len(categories), 6)

    def test_tax_piecewise_discovery_without_model(self):
        train, test = split_indices(len(self.df), Settings())
        tax = mine_tax_brackets(self.df, train, test)
        self.assertIsNotNone(tax)
        self.assertEqual(tax["base_name"], "four_component_sum")
        self.assertEqual(tax["thresholds"], [300.0, 600.0])
        self.assertEqual(tax["rates"], [0.055, 0.105, 0.17])
        self.assertEqual(tax["metrics"]["all"]["matched"], 1500)

    def test_standard_library_validator(self):
        with tempfile.TemporaryDirectory() as temporary:
            summary = check_file(SAMPLE, Path(temporary) / "issues.csv")
            self.assertEqual(summary["rows"], 1500)
            self.assertEqual(summary["F-INCOME"], 31)
            self.assertEqual(summary["F-ANNUAL"], 24)
            self.assertEqual(summary["F-TAX"], 0)
            self.assertEqual(summary["F-EXPENSE"], 28)
            self.assertEqual(summary["F-SAVINGS"], 25)

    def test_full_engine_reproduces_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            metadata = run(SAMPLE, Path(temporary), Settings())
            self.assertEqual(metadata["rows"], 1500)
            rules = {r["id"]: r for r in json.loads((Path(temporary) / "rules.json").read_text(encoding="utf-8"))}
            expected = {"F001": 1469, "F002": 1476, "F003": 1469, "F004": 1472,
                        "F005": 1475, "F006": 1500, "F007": 1479, "F008": 1480,
                        "F009": 1500, "T001": 1500, "M001": 1479,
                        "B001": 1482, "B002": 1478}
            for rule_id, count in expected.items():
                self.assertEqual(rules[rule_id]["metrics"]["all"]["matched"], count, rule_id)


if __name__ == "__main__":
    unittest.main()
