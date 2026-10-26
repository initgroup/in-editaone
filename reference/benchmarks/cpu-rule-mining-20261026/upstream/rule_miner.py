#!/usr/bin/env python3
"""국가통계 CSV 내검 규칙 발굴/검증 CLI.

실행: python rule_miner.py --input data/국가통계_가구생활조사_샘플.csv --output results

규칙 발견과 검증을 분리한다. 숫자 템플릿은 '가설'이며 실제 데이터에
대조하여 결과를 남긴다. 범주 매핑·구간·세율은 학습 부분집합에서 학습하고
분리한 검증 부분집합에서 검증한다. 데이터상 일치는 공식 업무 규칙의 증명이 아니다.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd


MISSING = "<결측>"
INCOME_PARTS = ["월근로소득_만원", "월사업소득_만원", "월이전소득_만원", "월기타소득_만원"]
EXPENSE_PARTS = ["식료품비_만원", "주거비_만원", "교육비_만원", "보건의료비_만원", "교통비_만원", "기타지출_만원"]
MAPPING_PAIRS = [
    ("시도코드", "시도명"),
    ("교육수준코드", "교육수준"),
    ("행정구역유형", "도시농촌구분"),
    ("가구원수", "가구원수구간"),
    ("종사상지위", "경제활동상태"),
]


@dataclass
class Settings:
    seed: int = 42
    test_fraction: float = 0.25
    min_support: int = 25
    min_confidence: float = 0.95
    min_validation_confidence: float = 0.90
    min_lift: float = 1.15
    max_if_rules: int = 90
    max_antecedents: int = 1


def read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            data = pd.read_csv(path, encoding=encoding, low_memory=False)
            data.columns = [str(c).strip() for c in data.columns]
            if data.columns.duplicated().any():
                raise ValueError("중복 열 이름이 있습니다.")
            if data.empty:
                raise ValueError("빈 CSV입니다.")
            return data.reset_index(drop=True)
        except UnicodeDecodeError:
            continue
    raise ValueError("CSV 인코딩을 인식할 수 없습니다. UTF-8 또는 CP949로 저장하세요.")


def split_indices(n: int, cfg: Settings) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(cfg.seed)
    perm = rng.permutation(n)
    test = np.zeros(n, dtype=bool)
    test[perm[: max(1, int(round(n * cfg.test_fraction)))]] = True
    return ~test, test


def as_label(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna(MISSING).astype(str)


def _plain(v: Any) -> str:
    if pd.isna(v):
        return MISSING
    if isinstance(v, (float, np.floating)):
        return f"{v:.8g}"
    return str(v)


def detect_tolerance(series: pd.Series) -> float:
    """데이터 저장 정밀도의 절반만 허용. 비율 등 한 자리 반올림은 0.051."""
    x = pd.to_numeric(series, errors="coerce").dropna().to_numpy(dtype=float)
    if len(x) == 0:
        return 1e-6
    for decimals in range(4):
        if np.all(np.abs(x - np.round(x, decimals)) <= 1e-8):
            return 1e-6 if decimals == 0 else 0.51 * 10 ** (-decimals)
    return 5.1e-5


def score(
    actual: pd.Series,
    predicted: pd.Series,
    applicable: np.ndarray,
    train: np.ndarray,
    test: np.ndarray,
    tolerance: float = 0.0,
) -> tuple[dict[str, Any], np.ndarray]:
    n = len(actual)
    if len(predicted) != n or len(applicable) != n:
        raise ValueError("검증 대상 행 수가 일치하지 않습니다.")
    valid = np.asarray(applicable, dtype=bool) & actual.notna().to_numpy() & predicted.notna().to_numpy()
    if tolerance:
        a = pd.to_numeric(actual, errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(predicted, errors="coerce").to_numpy(dtype=float)
        valid &= np.isfinite(a) & np.isfinite(b)
        matches = np.isclose(a, b, rtol=0, atol=tolerance) & valid
    else:
        matches = actual.astype(str).to_numpy() == predicted.astype(str).to_numpy()
        matches &= valid
    failure = valid & ~matches

    def met(mask: np.ndarray) -> dict[str, Any]:
        count = int((valid & mask).sum())
        hit = int((matches & mask).sum())
        return {"tested": count, "matched": hit, "violations": count - hit,
                "confidence": round(hit / count, 6) if count else None}

    stats = {"all": met(np.ones(n, dtype=bool)), "train": met(train), "validation": met(test),
             "not_evaluable": int((~valid).sum())}
    return stats, failure


def format_expression(rule_type: str, formula: str) -> str:
    return formula if rule_type in ("formula", "text_formula", "tax_formula", "numeric_bin") else formula


def add_rule(
    rules: list[dict[str, Any]],
    violations: list[dict[str, Any]],
    df: pd.DataFrame,
    train: np.ndarray,
    test: np.ndarray,
    *,
    rule_id: str,
    rule_type: str,
    method: str,
    name: str,
    expression: str,
    target: str,
    inputs: list[str],
    predicted: pd.Series,
    applicable: np.ndarray | None = None,
    tolerance: float = 0.0,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if applicable is None:
        applicable = np.ones(len(df), dtype=bool)
    stats, bad = score(df[target], predicted, applicable, train, test, tolerance)
    rule = {"id": rule_id, "type": rule_type, "method": method, "name": name,
            "expression": expression, "target": target, "inputs": inputs,
            "tolerance": tolerance, "metrics": stats}
    if extra:
        rule.update(extra)
    rules.append(rule)
    for i in np.flatnonzero(bad):
        actual_v = df.at[int(i), target]
        expected_v = predicted.iloc[int(i)]
        residual: float | None = None
        if tolerance:
            residual = round(float(actual_v) - float(expected_v), 6)
        violations.append({"rule_id": rule_id, "row_number": int(i) + 2,
                           "가구식별번호": str(df.iloc[int(i)].get("가구식별번호", f"row-{int(i) + 2}")),
                           "type": rule_type, "target": target,
                           "actual": _plain(actual_v), "expected": _plain(expected_v),
                           "residual": residual})
    return rule


def numeric_templates(df: pd.DataFrame) -> list[tuple[str, str, str, list[str], Callable[[pd.DataFrame], pd.Series], float]]:
    """업무 의미로 제안된 수식 *후보*. 매 실행마다 실측 검증한다."""
    candidates: list[tuple[str, str, str, list[str], Callable[[pd.DataFrame], pd.Series], float]] = [
        ("월총소득 합계", "월총소득_만원", "월총소득 = 월근로소득 + 월사업소득 + 월이전소득 + 월기타소득",
         INCOME_PARTS, lambda d: d[INCOME_PARTS].sum(axis=1, min_count=len(INCOME_PARTS)), 1e-6),
        ("연간소득 환산", "연간가구소득_만원", "연간가구소득 = 12 × 월총소득",
         ["월총소득_만원"], lambda d: 12 * d["월총소득_만원"], 1e-6),
        ("가처분소득", "가처분소득_만원", "가처분소득 = 월총소득 − 세금사회보험료",
         ["월총소득_만원", "세금사회보험료_만원"],
         lambda d: d["월총소득_만원"] - d["세금사회보험료_만원"], 1e-6),
        ("월총지출 합계", "월총지출_만원", "월총지출 = 식료품비 + 주거비 + 교육비 + 보건의료비 + 교통비 + 기타지출",
         EXPENSE_PARTS, lambda d: d[EXPENSE_PARTS].sum(axis=1, min_count=len(EXPENSE_PARTS)), 1e-6),
        ("월저축액", "월저축액_만원", "월저축액 = 가처분소득 − 월총지출",
         ["가처분소득_만원", "월총지출_만원"],
         lambda d: d["가처분소득_만원"] - d["월총지출_만원"], 1e-6),
        ("1인당 가처분소득", "1인당가처분소득_만원", "1인당가처분소득 = 가처분소득 / 가구원수",
         ["가처분소득_만원", "가구원수"],
         lambda d: d["가처분소득_만원"] / d["가구원수"].replace(0, np.nan), 0.051),
        ("균등화 가처분소득", "균등화가처분소득_만원", "균등화가처분소득 = 가처분소득 / SQRT(가구원수)",
         ["가처분소득_만원", "가구원수"],
         lambda d: d["가처분소득_만원"] / np.sqrt(d["가구원수"].where(d["가구원수"] > 0)), 0.051),
        ("주거비 부담률", "주거비부담률", "주거비부담률 = 100 × 주거비 / MAX(가처분소득, 1)",
         ["주거비_만원", "가처분소득_만원"],
         lambda d: 100 * d["주거비_만원"] / d["가처분소득_만원"].clip(lower=1), 0.051),
    ]
    return [c for c in candidates if all(key in df.columns for key in c[3] + [c[1]])]


def optimal_categorical_intervals(
    x: np.ndarray, y: np.ndarray, train: np.ndarray, n_bins: int, min_rows_per_bin: int = 12
) -> tuple[list[float], list[str]]:
    """CPU 동적계획법: 수치 X의 인접 구간별 다수결 오분류 합을 최소화한다.

    O(k*m^2 + m*c) 연산. m=서로 다른 입력값 수, c=범주 개수.
    GPU/AI 모델·딥러닝·외부 추론 서비스 사용 없음.
    """
    valid = train & np.isfinite(x)
    unique = np.unique(x[valid])
    categories = sorted(set(str(v) for v in y[valid]))
    if len(unique) < n_bins:
        raise ValueError("수치 구간 학습을 위한 입력값 종류가 부족합니다.")
    category_index = {v: i for i, v in enumerate(categories)}
    bin_number = np.searchsorted(unique, x[valid])
    counts = np.zeros((len(unique), len(categories)), dtype=int)
    for pos, label in zip(bin_number, y[valid]):
        counts[int(pos), category_index[str(label)]] += 1
    cumulative = np.vstack([np.zeros((1, len(categories)), dtype=int), counts.cumsum(axis=0)])
    m = len(unique)
    cost = np.full((m + 1, m + 1), np.inf)
    mode = np.full((m + 1, m + 1), -1, dtype=int)
    for lo in range(m):
        for hi in range(lo + 1, m + 1):
            catcounts = cumulative[hi] - cumulative[lo]
            total = int(catcounts.sum())
            if total < min_rows_per_bin:
                continue
            best_category = int(np.argmax(catcounts))
            cost[lo, hi] = total - int(catcounts[best_category])
            mode[lo, hi] = best_category

    dp = np.full((n_bins + 1, m + 1), np.inf)
    previous = np.full((n_bins + 1, m + 1), -1, dtype=int)
    dp[0, 0] = 0
    for k in range(1, n_bins + 1):
        for hi in range(k, m + 1):
            for lo in range(k - 1, hi):
                candidate = dp[k - 1, lo] + cost[lo, hi]
                if candidate < dp[k, hi]:
                    dp[k, hi] = candidate
                    previous[k, hi] = lo
    if not np.isfinite(dp[n_bins, m]):
        raise ValueError("최소 표본수 제한으로 구간을 나눌 수 없습니다.")

    segments = []
    hi = m
    for k in range(n_bins, 0, -1):
        lo = int(previous[k, hi])
        segments.append((lo, hi, categories[int(mode[lo, hi])]))
        hi = lo
    segments.reverse()
    boundaries = [round(float((unique[lo] + unique[lo - 1]) / 2), 8)
                  for lo, _, _ in segments[1:]]
    return boundaries, [label for _, _, label in segments]


def optimal_three_tax_intervals(x: np.ndarray, y: np.ndarray, train: np.ndarray) -> tuple[list[float], list[float], list[float], float] | None:
    """세금/소득 비율의 구간 내 제곱오차를 최소화하는 3분할 전수탐색.

    유일한 소득값 m개에 대해 O(m^2). 분할은 학습표본만 사용.
    """
    fit = train & np.isfinite(x) & np.isfinite(y) & (x >= 50)
    if int(fit.sum()) < 150:
        return None
    values = np.unique(x[fit])
    m = len(values)
    if m < 6:
        return None
    positions = np.searchsorted(values, x[fit])
    rates_all = y[fit] / x[fit]
    counts = np.bincount(positions, minlength=m)
    rates_sum = np.bincount(positions, weights=rates_all, minlength=m)
    rates_sq = np.bincount(positions, weights=rates_all ** 2, minlength=m)
    prefix_n = np.r_[0, counts.cumsum()]
    prefix_s = np.r_[0.0, rates_sum.cumsum()]
    prefix_q = np.r_[0.0, rates_sq.cumsum()]

    def error(lo: int, hi: int) -> float:
        cnt = prefix_n[hi] - prefix_n[lo]
        if cnt < 25:
            return float("inf")
        total = prefix_s[hi] - prefix_s[lo]
        return max(0.0, float(prefix_q[hi] - prefix_q[lo] - total * total / cnt))

    best = (float("inf"), 0, 0)
    for i in range(1, m - 1):
        left_error = error(0, i)
        if not np.isfinite(left_error):
            continue
        for j in range(i + 1, m):
            total = left_error + error(i, j) + error(j, m)
            if total < best[0]:
                best = (total, i, j)
    if not np.isfinite(best[0]):
        return None
    i, j = best[1], best[2]
    cuts = [float(values[i]), float(values[j])]  # 다음 구간의 첫 관측값
    raw_midpoints = [float((values[i - 1] + values[i]) / 2),
                     float((values[j - 1] + values[j]) / 2)]
    segment_rates = []
    for lower, upper in [(float("-inf"), cuts[0]), (cuts[0], cuts[1]), (cuts[1], float("inf"))]:
        mask = fit & (x >= lower) & (x < upper)
        segment_rates.append(round(float(np.median(y[mask] / x[mask])), 3))
    diffs = np.diff(values)
    quantum = round(float(np.min(diffs[diffs > 0])), 3)
    return cuts, raw_midpoints, segment_rates, quantum


def mine_tax_brackets(df: pd.DataFrame, train: np.ndarray, test: np.ndarray) -> dict[str, Any] | None:
    """세율=세금/기준소득의 구간별 잔차를 CPU 전수탐색, holdout으로 선택."""
    target = "세금사회보험료_만원"
    if target not in df.columns or not all(p in df.columns for p in INCOME_PARTS):
        return None
    bases: dict[str, pd.Series] = {"four_component_sum": df[INCOME_PARTS].sum(axis=1, min_count=4)}
    if "월총소득_만원" in df.columns:
        bases["reported_monthly_total"] = df["월총소득_만원"]

    trials = []
    y = df[target].to_numpy(dtype=float)
    for base_name, base_series in bases.items():
        x = base_series.to_numpy(dtype=float)
        result = optimal_three_tax_intervals(x, y, train)
        if result is None:
            continue
        cuts, midpoints, rates, quantum = result

        def tax_predict(value: float) -> float:
            if not np.isfinite(value):
                return float("nan")
            idx = 0 if value < cuts[0] else (1 if value < cuts[1] else 2)
            return round(float(value) * rates[idx], 1)  # Python round: 짝수 반올림/이진 실수 영향 포함

        predicted = pd.Series([tax_predict(z) for z in x], index=df.index)
        stats, _ = score(df[target], predicted, np.isfinite(x), train, test, 1e-6)
        if stats["validation"]["tested"] < 20:
            continue
        trials.append({"base_name": base_name, "base": base_series, "predicted": predicted,
                       "thresholds_raw": midpoints, "thresholds": cuts, "rates": rates,
                       "quantum": quantum, "metrics": stats})
    if not trials:
        return None
    return max(trials, key=lambda t: (t["metrics"]["validation"]["confidence"],
                                      t["metrics"]["all"]["confidence"],
                                      t["metrics"]["train"]["confidence"]))


def make_derived_categorical(df: pd.DataFrame) -> dict[str, pd.Series]:
    output: dict[str, pd.Series] = {}
    for col in ("산업분류", "통근시간_분", "주당근로시간"):
        if col in df.columns:
            output[f"{col}__입력상태"] = pd.Series(np.where(df[col].notna(), "입력", "결측"), index=df.index)
    for col in ("월근로소득_만원", "월사업소득_만원", "아파트층수"):
        if col in df.columns:
            numeric = pd.to_numeric(df[col], errors="coerce")
            output[f"{col}__양수여부"] = pd.Series(np.where(numeric.gt(0), "양수", "영또는음수"), index=df.index)
    return output


def mine_mappings(df: pd.DataFrame, train: np.ndarray, test: np.ndarray,
                  rules: list[dict[str, Any]], violations: list[dict[str, Any]]) -> None:
    for left, right in MAPPING_PAIRS:
        if left not in df or right not in df:
            continue
        a, b = as_label(df[left]), as_label(df[right])
        learned: dict[str, str] = {}
        for key, group in b[train].groupby(a[train]):
            if key == MISSING:
                continue
            mode = group.mode()
            if not mode.empty:
                learned[str(key)] = str(mode.iloc[0])
        predicted = a.map(learned)
        applicable = (a != MISSING).to_numpy() & predicted.notna().to_numpy()
        add_rule(rules, violations, df.assign(**{right: b}), train, test,
                 rule_id=f"M{len([r for r in rules if r['type'] == 'mapping']) + 1:03d}",
                 rule_type="mapping", method="train_majority_lookup",
                 name=f"{left}별 {right} 매핑",
                 expression=f"IF {left}=k THEN {right}=LOOKUP(k)",
                 target=right, inputs=[left], predicted=predicted,
                 applicable=applicable, extra={"mapping": learned,
                                               "unseen_predictor_rows": int((~applicable).sum())})


def mine_numeric_bins(df: pd.DataFrame, train: np.ndarray, test: np.ndarray,
                      rules: list[dict[str, Any]], violations: list[dict[str, Any]]) -> None:
    candidates = [("가구주연령", "가구주연령대", 6), ("가구원수", "가구원수구간", 4)]
    for left, right, max_leaves in candidates:
        if left not in df or right not in df:
            continue
        x = pd.to_numeric(df[left], errors="coerce")
        y = as_label(df[right])
        thresholds, labels_by_bin = optimal_categorical_intervals(
            x.to_numpy(dtype=float), y.to_numpy(), train, max_leaves)
        bin_idx = np.searchsorted(thresholds, x.fillna(-999999).to_numpy(dtype=float), side="right")
        predicted = pd.Series([labels_by_bin[int(i)] for i in bin_idx], index=df.index)
        labels = []
        all_bounds = [-np.inf] + thresholds + [np.inf]
        for lo, hi, label in zip(all_bounds[:-1], all_bounds[1:], labels_by_bin):
            labels.append({"greater_than": None if not np.isfinite(lo) else lo,
                           "at_most": None if not np.isfinite(hi) else hi, "expected": label})
        add_rule(rules, violations, df.assign(**{right: y}), train, test,
                 rule_id=f"B{len([r for r in rules if r['type'] == 'numeric_bin']) + 1:03d}",
                 rule_type="numeric_bin", method="contiguous_majority_dynamic_programming_cpu",
                 name=f"{left}에서 {right} 구간 도출",
                 expression=f"IF {left} falls in learned interval THEN {right}=interval label",
                 target=right, inputs=[left], predicted=predicted,
                 applicable=x.notna().to_numpy(), extra={"bins": labels})


def _category_fields(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    excluded = {"가구식별번호", "조사구식별번호", "표본조사구코드", "층화코드", "조사일자", "응답자메모", "조사연도"}
    predictors, targets = [], []
    for col in df.columns:
        if col in excluded:
            continue
        count = df[col].nunique(dropna=True)
        if 2 <= count <= 20 and (pd.api.types.is_object_dtype(df[col]) or
                                 isinstance(df[col].dtype, pd.StringDtype) or
                                 col in ("가구원수", "교육수준코드", "조사차수", "건강상태등급", "삶의만족도점수")):
            predictors.append(col)
            targets.append(col)
    return predictors, targets


def mine_single_if(df: pd.DataFrame, train: np.ndarray, test: np.ndarray,
                   cfg: Settings) -> list[dict[str, Any]]:
    derived = make_derived_categorical(df)
    augmented = df.assign(**derived)
    predictors, targets = _category_fields(df)
    targets += list(derived)
    fields = {col: as_label(augmented[col]) for col in predictors + targets}
    candidates: list[dict[str, Any]] = []

    for source in predictors:
        src = fields[source]
        counts = src[train].value_counts()
        for value, ntrain in counts.items():
            if value == MISSING or ntrain < cfg.min_support:
                continue
            condition = src.eq(value).to_numpy()
            if int((condition & test).sum()) < 6:
                continue
            for target in targets:
                if target == source or target.startswith(f"{source}__"):
                    continue  # 같은 변수의 단순 파생값은 자명하므로 제외
                tgt = fields[target]
                train_y = tgt[condition & train]
                mode = train_y.mode()
                if mode.empty or mode.iloc[0] == MISSING and target not in derived:
                    continue
                chosen = str(mode.iloc[0])
                matched = tgt.eq(chosen).to_numpy()
                train_rate = float(matched[condition & train].mean())
                test_rate = float(matched[condition & test].mean())
                full_rate = float(matched[condition].mean())
                if min(train_rate, full_rate) < cfg.min_confidence or test_rate < cfg.min_validation_confidence:
                    continue
                prevalence = float(matched.mean())
                lift = float(full_rate / prevalence) if prevalence else 0
                if lift < cfg.min_lift:
                    continue
                candidates.append({"type": "if_then", "source": source, "value": value,
                                   "target": target, "then": chosen, "condition": condition,
                                   "matched": matched, "train_confidence": train_rate,
                                   "validation_confidence": test_rate, "confidence": full_rate,
                                   "lift": lift, "support": int(condition.sum()),
                                   "description": f"IF {source} = '{value}' THEN {target} = '{chosen}'"})

    # 같은 원인/결과 조합에서 아주 희소한 값만 늘어놓지 않도록 상위 6개로 제한.
    candidates.sort(key=lambda r: (-r["support"] * (r["lift"] ** 0.3), -r["confidence"], r["description"]))
    retained: list[dict[str, Any]] = []
    pair_counter: Counter[tuple[str, str]] = Counter()
    for item in candidates:
        key = (item["source"], item["target"])
        if pair_counter[key] >= 6:
            continue
        retained.append(item)
        pair_counter[key] += 1
        if len(retained) >= cfg.max_if_rules:
            break
    return retained


def mine_pair_if(df: pd.DataFrame, train: np.ndarray, test: np.ndarray,
                 cfg: Settings, unaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if cfg.max_antecedents < 2:
        return []
    derived = make_derived_categorical(df)
    augmented = df.assign(**derived)
    _, target_names = _category_fields(df)
    target_names += list(derived)
    pairs = [("종사상지위", "주택유형"), ("행정구역유형", "주택유형"),
             ("가구유형", "종사상지위"), ("가구유형", "점유형태"),
             ("경제활동상태", "주택유형"), ("점유형태", "종사상지위")]
    fields = {col: as_label(augmented[col]) for col in set(sum((list(p) for p in pairs), []) + target_names) if col in augmented}
    result = []
    for a, b in pairs:
        if a not in fields or b not in fields:
            continue
        A, B = fields[a], fields[b]
        for (va, vb), subset in augmented.loc[train].groupby([a, b], dropna=False):
            if pd.isna(va) or pd.isna(vb) or len(subset) < cfg.min_support:
                continue
            mask = A.eq(str(va)).to_numpy() & B.eq(str(vb)).to_numpy()
            if int((mask & test).sum()) < 6:
                continue
            for target in target_names:
                if target in (a, b) or target.startswith(f"{a}__") or target.startswith(f"{b}__"):
                    continue
                tgt = fields[target]
                mode = tgt[mask & train].mode()
                if mode.empty or str(mode.iloc[0]) == MISSING and target not in derived:
                    continue
                val = str(mode.iloc[0])
                hit = tgt.eq(val).to_numpy()
                tr = float(hit[mask & train].mean())
                va_rate = float(hit[mask & test].mean())
                full = float(hit[mask].mean())
                marginal = float(hit.mean())
                lift = full / marginal if marginal else 0
                if min(tr, full) < max(cfg.min_confidence, .98) or va_rate < cfg.min_validation_confidence or lift < cfg.min_lift:
                    continue
                # 같은 결론이 단일 조건에서도 성립하면 불필요한 복합 규칙은 제외.
                baseline = max((u["confidence"] for u in unaries
                                if u["target"] == target and u["then"] == val and
                                ((u["source"] == a and u["value"] == str(va)) or
                                 (u["source"] == b and u["value"] == str(vb)))), default=0)
                if baseline and full < baseline + .01:
                    continue
                result.append({"type": "if_then_2", "source": [a, b], "value": [str(va), str(vb)],
                               "target": target, "then": val, "condition": mask,
                               "matched": hit, "train_confidence": tr,
                               "validation_confidence": va_rate, "confidence": full,
                               "lift": lift, "support": int(mask.sum()),
                               "description": f"IF {a}='{va}' AND {b}='{vb}' THEN {target}='{val}'"})
    result.sort(key=lambda r: (-r["support"] * r["lift"] ** .3, -r["confidence"]))
    return result[:20]


def append_if_rules(df: pd.DataFrame, train: np.ndarray, test: np.ndarray,
                    candidates: list[dict[str, Any]], rules: list[dict[str, Any]],
                    violations: list[dict[str, Any]]) -> None:
    augmented = df.assign(**make_derived_categorical(df))
    for i, item in enumerate(candidates, 1):
        target = item["target"]
        actual = as_label(augmented[target])
        predicted = pd.Series(item["then"], index=df.index)
        inputs = item["source"] if isinstance(item["source"], list) else [item["source"]]
        add_rule(rules, violations, df.assign(**{target: actual}), train, test,
                 rule_id=f"C{i:03d}", rule_type=item["type"], method="frequency_mode_holdout",
                 name=item["description"], expression=item["description"],
                 target=target, inputs=inputs, predicted=predicted, applicable=item["condition"],
                 extra={"lift": round(item["lift"], 4), "antecedent_support": item["support"]})


def mine_text_formula(df: pd.DataFrame, train: np.ndarray, test: np.ndarray,
                      rules: list[dict[str, Any]], violations: list[dict[str, Any]]) -> None:
    cols = ("시도코드", "행정구역유형", "층화코드")
    if not all(c in df for c in cols):
        return
    expected = "ST-" + df["시도코드"].astype(str).str.removeprefix("R") + "-" + df["행정구역유형"].astype(str).str[0]
    add_rule(rules, violations, df, train, test, rule_id="T001", rule_type="text_formula",
             method="constructed_string_hypothesis_verified", name="층화코드 구성",
             expression="층화코드 = 'ST-' + 시도코드에서 'R' 제거 + '-' + 행정구역유형 첫 글자",
             target="층화코드", inputs=["시도코드", "행정구역유형"], predicted=expected)


def auto_arithmetic_candidates(df: pd.DataFrame, train: np.ndarray, test: np.ndarray,
                               max_results: int = 45) -> list[dict[str, Any]]:
    """별도 자동 스크리닝. 최종 확정 규칙이 아니라 사람이 검토할 후보들."""
    numeric = [c for c in df.select_dtypes(include="number").columns
               if c not in {"조사연도", "조사차수", "교육수준코드", "건강상태등급", "삶의만족도점수", "지역박탈도백분위"}
               and c != "조사가중치" and df[c].nunique(dropna=True) > 10]
    if not numeric:
        return []
    inputs = [c for c in numeric if c != "경제스트레스지수"] + (["가구원수"] if "가구원수" in df else [])
    targets = [c for c in numeric if c.endswith("_만원") or c == "주거비부담률"]
    array = {c: pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=float) for c in set(targets + inputs)}
    seen: set[tuple[str, str]] = set()
    found: list[dict[str, Any]] = []
    n = len(df)

    def consider(ycol: str, expression: str, z: np.ndarray, sources: list[str]) -> None:
        key = (ycol, expression)
        if key in seen:
            return
        seen.add(key)
        with np.errstate(invalid="ignore"):
            valid = np.isfinite(z) & np.isfinite(array[ycol])
        if valid.sum() < int(.975 * n) or (valid & test).sum() < 15:
            return
        tol = detect_tolerance(df[ycol])
        same = np.isclose(array[ycol], z, rtol=0, atol=tol) & valid
        tr_rate = same[valid & train].mean()
        va_rate = same[valid & test].mean()
        full_rate = same[valid].mean()
        if min(tr_rate, va_rate, full_rate) < .96:
            return
        found.append({"target": ycol, "expression": expression, "inputs": sources,
                      "train_confidence": round(float(tr_rate), 6),
                      "validation_confidence": round(float(va_rate), 6),
                      "matched": int(same.sum()), "tested": int(valid.sum()),
                      "confidence": round(float(full_rate), 6), "tolerance": tol})

    for ycol in targets:
        y = array[ycol]
        for a in inputs:
            if a == ycol:
                continue
            x = array[a]
            valid = train & np.isfinite(x) & np.isfinite(y) & (np.abs(x) > 1e-9)
            if valid.sum() > .6 * n:
                scale = round(float(np.median(y[valid] / x[valid])), 5)
                if abs(scale) >= 1e-5 and abs(scale) <= 1000:
                    consider(ycol, f"{scale:g} × {a}", scale * x, [a])
        for ia, a in enumerate(inputs):
            if a == ycol:
                continue
            x = array[a]
            for b in inputs[ia + 1:]:
                if b == ycol:
                    continue
                z = array[b]
                with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
                    consider(ycol, f"{a} + {b}", x + z, [a, b])
                    consider(ycol, f"{a} - {b}", x - z, [a, b])
                    consider(ycol, f"{b} - {a}", z - x, [b, a])
                    consider(ycol, f"{a} / {b}", x / z, [a, b])
                    consider(ycol, f"{b} / {a}", z / x, [b, a])
                    consider(ycol, f"100 × {a} / {b}", 100 * x / z, [a, b])
                    consider(ycol, f"100 × {b} / {a}", 100 * z / x, [b, a])
                    consider(ycol, f"{a} / sqrt({b})", x / np.sqrt(np.where(z > 0, z, np.nan)), [a, b])
                    consider(ycol, f"{b} / sqrt({a})", z / np.sqrt(np.where(x > 0, x, np.nan)), [b, a])
    found.sort(key=lambda r: (-r["confidence"], -r["tested"], len(r["expression"]), r["expression"]))
    final: list[dict[str, Any]] = []
    per_target: Counter[str] = Counter()
    for item in found:
        if per_target[item["target"]] >= 5:
            continue
        final.append(item)
        per_target[item["target"]] += 1
        if len(final) >= max_results:
            break
    return final


def save_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def export_report(output: Path, df: pd.DataFrame, rules: list[dict[str, Any]],
                  violations: list[dict[str, Any]], screened: list[dict[str, Any]],
                  source_path: Path, test: np.ndarray) -> None:
    formula = [r for r in rules if r["type"] in ("formula", "tax_formula", "text_formula")]
    maps = [r for r in rules if r["type"] == "mapping"]
    bins = [r for r in rules if r["type"] == "numeric_bin"]
    conds = [r for r in rules if r["type"] in ("if_then", "if_then_2")]
    unique_bad = {r["가구식별번호"] for r in violations}
    lines = [
        "# 가구생활조사 CSV 내검규칙 분석 결과",
        "",
        f"- 원본: `{source_path.name}`",
        f"- 규모: **{len(df):,}행 × {len(df.columns)}열**",
        f"- 검증: 학습 {len(df) - int(test.sum()):,}행 / 분리 검증 {int(test.sum()):,}행 (난수 시드 42)",
        f"- 출력 규칙: 수식 {len(formula)}, 범주 매핑 {len(maps)}, 수치구간 {len(bins)}, IF–THEN {len(conds)}",
        f"- 적어도 한 규칙에서 위반된 가구: **{len(unique_bad):,}개**. 같은 행의 중복 위반은 별도 규칙별로 기록.",
        "",
        "## 1. 검증된 수식 후보",
        "",
        "| 규칙 ID | 수식 | 전체 일치 | 전체 신뢰도 | 검증셋 신뢰도 |",
        "|---|---|---:|---:|---:|",
    ]
    for r in formula:
        allm = r["metrics"]["all"]
        val = r["metrics"]["validation"]
        lines.append(f"| {r['id']} | {r['expression']} | {allm['matched']:,}/{allm['tested']:,} | {100*allm['confidence']:.2f}% | {100*val['confidence']:.2f}% |")
    lines += ["", "**반올림 유의:** 나눗셈·비율은 기록값이 소수점 한 자리라 ±0.051 허용. 기타 산술 합계와 세율식은 엄격 비교.",
              "세율은 네 가지 소득 원천 합계와 보고된 월총소득을 **각각** 후보로 놓고, 학습표본에서 세율 3구간을 추정한 뒤 검증표본에 비교 적용함.", "",
              "## 2. 코드·범주 매핑", "", "| ID | 매핑 | 일치 | 위반 | 검증셋 신뢰도 |", "|---|---|---:|---:|---:|"]
    for r in maps:
        m = r["metrics"]["all"]
        v = r["metrics"]["validation"]
        lines.append(f"| {r['id']} | {r['inputs'][0]} → {r['target']} | {m['matched']:,}/{m['tested']:,} | {m['violations']} | {100*v['confidence']:.2f}% |")
    lines += ["", "숫자 구간은 학습표본의 연속 구간 최빈값 오류를 최소화하는 CPU 동적계획법으로 도출했으며, 실제 조사표의 공식 코드표를 뜻하지 않습니다.", ""]
    for r in bins:
        m = r["metrics"]["all"]
        lines.append(f"- **{r['id']}** {r['inputs'][0]} → {r['target']}: {m['matched']:,}/{m['tested']:,} 일치; 구간 {r['bins']}")
    lines += ["", "## 3. IF–THEN 조건 규칙 (대표)", "",
              "조건 규칙의 분모는 IF 선행조건을 만족하는 건수이며, lift는 결과값의 전체 발생률 대비 배수입니다.", "",
              "| ID | 조건 → 결과 | 일치/적용 | 신뢰도 | lift |", "|---|---|---:|---:|---:|"]
    # 목적이 다른 예시를 보여주고 동일 계열 규칙의 반복 표시를 줄인다.
    example_patterns = [
        ("행정구역유형 = '동부'", "도시농촌구분"),
        ("경제활동상태 = '취업'", "산업분류__입력상태"),
        ("경제활동상태 = '비경제활동'", "통근시간_분__입력상태"),
        ("주택유형 = '아파트'", "아파트층수__양수여부"),
        ("주택유형 = '단독주택'", "아파트층수__양수여부"),
        ("가구유형 = '1인가구'", "가구원수 = '1'"),
        ("가구유형 = '부부'", "가구원수 = '2'"),
        ("종사상지위 = '상용근로자'", "월근로소득_만원__양수여부"),
        ("종사상지위 = '자영업자'", "월사업소득_만원__양수여부"),
        ("종사상지위 = '실업자'", "경제활동상태 = '실업'"),
        ("종사상지위 = '임시·일용근로자'", "경제활동상태 = '취업'"),
        ("응답방식 = '인터넷'", "인터넷이용여부"),
        ("교육수준코드 = '5'", "교육수준"),
        ("가구원수 = '1'", "가구원수구간"),
        ("시도코드 = 'R01'", "시도명"),
        ("산업분류 = '제조업'", "경제활동상태"),
    ]
    selected = []
    for left, right in example_patterns:
        match = next((r for r in conds if r["expression"].startswith(f"IF {left}") and right in r["expression"]), None)
        if match and match not in selected:
            selected.append(match)
    if not selected:
        selected = conds[:18]
    for r in selected:
        m = r["metrics"]["all"]
        lines.append(f"| {r['id']} | {r['expression']} | {m['matched']:,}/{m['tested']:,} | {100*m['confidence']:.2f}% | {r['lift']:.2f} |")
    lines += ["", f"그 밖의 IF–THEN 규칙을 포함한 전체 {len(conds)}개는 `rules.json`에서 확인할 수 있습니다.", "",
              "## 4. 예외 탐지와 해석", "",
              "- 규칙별 불일치 상세는 `violations.csv`(원본 CSV 행번호와 가구식별번호 포함). 같은 가구의 여러 규칙 위반을 무조건 독립 오류로 합산하지 마세요.",
              "- `flagged_households.csv`는 위반 가구를 중복 제거해 정렬한 파일입니다.",
              "- 실제 오류, 응답 특례, 코드표 변경, 데이터 가공 오류, 계산결과의 연쇄 불일치를 구분해야 합니다.",
              "- `screened_formulas.json`은 여러 숫자 열에 대한 자동 1·2변수 탐색 결과이며, **수식 후보**이므로 업무 확정 규칙과 분리했습니다.",
              "- 식별번호/행번호, 조사구 코드, 날짜·메모, 상수 연도는 가짜 연관규칙을 만들기 쉬워 조건 탐색에서 제외했습니다.",
              "- 샘플 내 높은 정확도는 인과관계나 국가통계의 공식 편집 규칙을 입증하지 않습니다. 별도 연도·지역의 외부 검증이 필요합니다.",
              "",
              "## 5. 실제 실행 로직", "",
              "1. UTF-8 BOM/CP949로 입력, 결측과 숫자 형식을 유지하여 열 프로파일링.",
              "2. 난수 시드 42로 무작위 75% 학습/25% 검증 분리. 원본 순번의 주기적 패턴은 학습에 사용하지 않음.",
              "3. 범주 규칙: 학습표본의 조건별 최빈 결과 추정 → 적용건수·신뢰도·lift 검사 → 분리 검증표본으로 재검증.",
              "4. 그룹 매핑: 예를 들어 시도코드→시도명의 다중 값 매핑을 학습표본에서 추정하고 전체·검증표본에 적용.",
              "5. 구간 규칙: 연령/가구원수→범주를 연속한 6/4구간의 최빈값 불일치 건수를 최소화하는 CPU 동적계획법으로 탐색.",
              "6. 수식 규칙: 합계/차이/곱/비율/제곱근을 후보로 구성하고 반올림 허용오차·불일치 행 확인.",
              "7. 세율식: 소득 4항목 합과 월총소득을 각 후보로, 세금÷기준소득 비율의 오차제곱합을 최소화하는 3구간을 CPU 전수탐색.",
              "8. 전체 1,500건과 보류 검증 375건에 대해 재평가하여 규칙·예외 CSV/JSON 저장.",
              "",
              "## 6. 한계 및 후속 개선", "",
              "- 본 실행 코드는 **AI 모델 추론, LLM 호출, GPU, scikit-learn 의존성 없이** pandas/NumPy의 CPU 산술·빈도집계·전수탐색·동적계획법만 사용합니다.",
              "- 현재 계산식은 설명 가능한 후보식과 자동 단변수·2변수 연산 탐색이며, 일반적인 비선형 **심볼릭 회귀(PySR/GP)** 전반을 탐색하지 않습니다.",
              "- 다중 선행 조건은 의미 있는 일부 필드 조합만 탐색합니다. 대규모 데이터에서는 Apriori/FP-Growth 또는 트리 기반 후보 생성으로 확장할 수 있습니다.",
              "- 스코어 기준 및 최소 표본수를 규칙 유형별로 조절하고, 신뢰구간·다중가설 검정·시점 외 검증을 추가하세요.",
              "- 실제 INIT Data Editing System 연결 시 원본/프로파일/규칙/위반 레포지토리를 구분하고 검수자 승인 없이 자동 수정하지 마세요.",
              ""]
    (output / "ANALYSIS_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def run(input_path: Path, output: Path, cfg: Settings) -> dict[str, Any]:
    df = read_csv(input_path)
    output.mkdir(parents=True, exist_ok=True)
    train, test = split_indices(len(df), cfg)
    rules: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []

    for i, (name, target, expr, inputs, calculator, tolerance) in enumerate(numeric_templates(df), 1):
        predicted = pd.to_numeric(calculator(df), errors="coerce")
        add_rule(rules, violations, df, train, test, rule_id=f"F{i:03d}",
                 rule_type="formula", method="domain_arithmetic_candidate_verified",
                 name=name, expression=expr, target=target, inputs=inputs,
                 predicted=predicted, tolerance=tolerance)

    tax = mine_tax_brackets(df, train, test)
    if tax:
        c1, c2 = tax["thresholds"]
        rates = tax["rates"]
        base_expr = " + ".join(INCOME_PARTS) if tax["base_name"] == "four_component_sum" else "월총소득_만원"
        formula = (f"x={base_expr}; 세금사회보험료 = ROUND(x × "
                   f"(x<{c1:g}: {rates[0]:g} / {c1:g}≤x<{c2:g}: {rates[1]:g} / "
                   f"x≥{c2:g}: {rates[2]:g}), 1)")
        add_rule(rules, violations, df, train, test, rule_id="F009", rule_type="tax_formula",
                 method="three_interval_ratio_sse_exhaustive_cpu",
                 name="세율 구간 탐색", expression=formula, target="세금사회보험료_만원",
                 inputs=INCOME_PARTS if tax["base_name"] == "four_component_sum" else ["월총소득_만원"],
                 predicted=tax["predicted"], tolerance=1e-6,
                 extra={"selected_base": tax["base_name"], "learned_cutoffs": tax["thresholds"],
                        "observed_value_midpoints": tax["thresholds_raw"], "rates": rates,
                        "observed_input_quantum": tax["quantum"]})

    mine_text_formula(df, train, test, rules, violations)
    mine_mappings(df, train, test, rules, violations)
    mine_numeric_bins(df, train, test, rules, violations)
    unary = mine_single_if(df, train, test, cfg)
    pair = mine_pair_if(df, train, test, cfg, unary)
    append_if_rules(df, train, test, unary + pair, rules, violations)
    screened = auto_arithmetic_candidates(df, train, test)
    save_csv(output / "violations.csv", violations,
             ["rule_id", "row_number", "가구식별번호", "type", "target", "actual", "expected", "residual"])
    flagged: dict[str, list[str]] = defaultdict(list)
    for row in violations:
        flagged[row["가구식별번호"]].append(row["rule_id"])
    save_csv(output / "flagged_households.csv", [
        {"가구식별번호": hid, "violated_rule_count": len(items), "rule_ids": ";".join(sorted(items))}
        for hid, items in sorted(flagged.items())], ["가구식별번호", "violated_rule_count", "rule_ids"])
    (output / "rules.json").write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "screened_formulas.json").write_text(json.dumps(screened, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata = {"source_filename": input_path.name,
                "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
                "rows": len(df), "columns": len(df.columns),
                "train_rows": int(train.sum()), "validation_rows": int(test.sum()),
                "settings": vars(cfg), "rule_count": len(rules),
                "rule_types": dict(Counter(r["type"] for r in rules)),
                "violation_rows": len(violations), "flagged_households": len(flagged),
                "auto_screened_candidates": len(screened),
                "missing_count_by_column": {str(c): int(v) for c, v in df.isna().sum().items()}}
    (output / "run_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    export_report(output, df, rules, violations, screened, input_path, test)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="CSV에서 IF-THEN과 F(X)=Y 내검 규칙 발굴/검증")
    parser.add_argument("--input", type=Path, required=True, help="분석할 원본 CSV")
    parser.add_argument("--output", type=Path, default=Path("results"), help="결과 폴더")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-fraction", type=float, default=0.25)
    parser.add_argument("--min-support", type=int, default=25)
    parser.add_argument("--min-confidence", type=float, default=0.95)
    parser.add_argument("--min-validation-confidence", type=float, default=0.90)
    parser.add_argument("--min-lift", type=float, default=1.15)
    parser.add_argument("--max-if-rules", type=int, default=90)
    parser.add_argument("--max-antecedents", type=int, choices=[1, 2], default=1)
    opts = parser.parse_args()
    if not 0 < opts.test_fraction < 1:
        parser.error("--test-fraction은 0과 1 사이여야 합니다.")
    cfg = Settings(seed=opts.seed, test_fraction=opts.test_fraction,
                   min_support=opts.min_support, min_confidence=opts.min_confidence,
                   min_validation_confidence=opts.min_validation_confidence,
                   min_lift=opts.min_lift, max_if_rules=opts.max_if_rules,
                   max_antecedents=opts.max_antecedents)
    print(json.dumps(run(opts.input, opts.output, cfg), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
