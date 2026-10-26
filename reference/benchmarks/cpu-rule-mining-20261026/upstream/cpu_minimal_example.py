#!/usr/bin/env python3
"""Python 표준 라이브러리만 사용하는 CPU 전용 가구생활조사 규칙 검증 예제.

이 파일은 발굴된 규칙을 '검증'한다. 신규 규칙의 자동 발견은 rule_miner.py.
외부 API, LLM, GPU, 머신러닝 패키지 호출이 없다.

python cpu_minimal_example.py --input data/국가통계_가구생활조사_샘플.csv \
    --output results/minimal_violations.csv
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter
from pathlib import Path


INCOME_FIELDS = ("월근로소득_만원", "월사업소득_만원", "월이전소득_만원", "월기타소득_만원")
SPENDING_FIELDS = ("식료품비_만원", "주거비_만원", "교육비_만원", "보건의료비_만원", "교통비_만원", "기타지출_만원")


def num(record: dict[str, str], key: str) -> float:
    value = record[key].strip()
    if value == "":
        raise ValueError(f"{key}: 결측")
    return float(value)


def tax_formula(record: dict[str, str]) -> float:
    income = sum(num(record, k) for k in INCOME_FIELDS)
    rate = 0.055 if income < 300 else 0.105 if income < 600 else 0.17
    return round(income * rate, 1)


def evaluate_record(record: dict[str, str]) -> list[tuple[str, str, str]]:
    """(rule_id, expected, actual) 위반 목록. 계산 가능 데이터만 수식 검증."""
    violations: list[tuple[str, str, str]] = []

    def rule_bool(rule_id: str, condition: bool, expected: str, actual: str) -> None:
        if not condition:
            violations.append((rule_id, expected, actual))

    def numeric_rule(rule_id: str, field: str, predicted: float, tolerance: float = 1e-6) -> None:
        if math.isfinite(predicted) and not math.isclose(num(record, field), predicted, rel_tol=0, abs_tol=tolerance):
            violations.append((rule_id, f"{predicted:.6g}", record[field]))

    # IF–THEN 내검. 선행 조건을 만족하는 행에만 후행 조건 적용.
    if record["주택유형"] == "아파트":
        rule_bool("C-APARTMENT", num(record, "아파트층수") > 0, "아파트층수 > 0", record["아파트층수"])
    else:
        rule_bool("C-NON-APARTMENT", num(record, "아파트층수") == 0, "아파트층수 = 0", record["아파트층수"])
    if record["가구유형"] == "1인가구":
        rule_bool("C-SINGLE", num(record, "가구원수") == 1, "가구원수 = 1", record["가구원수"])
    if record["종사상지위"] == "자영업자":
        rule_bool("C-SELF-EMPLOYED", num(record, "월사업소득_만원") > 0,
                  "월사업소득_만원 > 0", record["월사업소득_만원"])
    if record["경제활동상태"] == "취업":
        rule_bool("C-INDUSTRY", record["산업분류"].strip() != "", "산업분류 입력", record["산업분류"])
    if num(record, "가구주연령") >= 70:
        rule_bool("C-AGE70", record["가구주연령대"] == "70대 이상", "70대 이상", record["가구주연령대"])

    # F(X)=Y 내검. 실제로 기록된 값과 직접 계산값을 비교하며 데이터를 고치지 않는다.
    total_income = sum(num(record, k) for k in INCOME_FIELDS)
    numeric_rule("F-INCOME", "월총소득_만원", total_income)
    numeric_rule("F-ANNUAL", "연간가구소득_만원", 12 * num(record, "월총소득_만원"))
    numeric_rule("F-TAX", "세금사회보험료_만원", tax_formula(record))
    numeric_rule("F-DISPOSABLE", "가처분소득_만원", num(record, "월총소득_만원") - num(record, "세금사회보험료_만원"))
    total_expense = sum(num(record, k) for k in SPENDING_FIELDS)
    numeric_rule("F-EXPENSE", "월총지출_만원", total_expense)
    numeric_rule("F-SAVINGS", "월저축액_만원", num(record, "가처분소득_만원") - num(record, "월총지출_만원"))
    count = num(record, "가구원수")
    if count > 0:
        numeric_rule("F-PERCAPITA", "1인당가처분소득_만원", num(record, "가처분소득_만원") / count, .051)
        numeric_rule("F-EQUIV", "균등화가처분소득_만원", num(record, "가처분소득_만원") / math.sqrt(count), .051)
    housing_denominator = max(num(record, "가처분소득_만원"), 1)
    numeric_rule("F-HOUSING", "주거비부담률", 100 * num(record, "주거비_만원") / housing_denominator, .051)
    return violations


def check_file(source: Path, output: Path) -> Counter[str]:
    results: Counter[str] = Counter()
    output.parent.mkdir(parents=True, exist_ok=True)
    with source.open("r", encoding="utf-8-sig", newline="") as inp, output.open("w", encoding="utf-8-sig", newline="") as out:
        reader = csv.DictReader(inp)
        writer = csv.writer(out)
        writer.writerow(["row_number", "가구식별번호", "rule_id", "expected", "actual"])
        for row_no, row in enumerate(reader, 2):
            results["rows"] += 1
            for rule_id, expected, actual in evaluate_record(row):
                writer.writerow([row_no, row.get("가구식별번호", ""), rule_id, expected, actual])
                results["violations"] += 1
                results[rule_id] += 1
    return results


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Python 표준 라이브러리만으로 IF–THEN/F(X)=Y 검증")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, default=Path("results/minimal_violations.csv"))
    args = p.parse_args()
    summary = check_file(args.input, args.output)
    print(f"검증 {summary['rows']:,}건 / 위반 {summary['violations']:,}건")
    for rule_id, n in sorted(summary.items()):
        if rule_id not in ("rows", "violations"):
            print(f"  {rule_id}: {n:,}건")
    print(f"상세 파일: {args.output}")
