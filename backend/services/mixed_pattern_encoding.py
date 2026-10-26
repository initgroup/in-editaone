"""Train-only numeric-text views for actual-column condition rules.

Low-cardinality text codes retain their existing categorical interpretation.
Physical source values are never replaced; emitted numeric predicates must carry
numericText so SQL detection and final editing use the same strict parser.
"""
from __future__ import annotations

import numpy as np

from backend.services.mixed_numeric import TEXT_TYPES, inspect_numeric_text, parse_numeric_decimal


def condition_numeric_views(rows, columns, train_indices, *, category_limit, excluded):
    inferred, diagnostics = set(), []
    target_rows = rows
    for column in columns:
        name = column["name"]
        if name in excluded or column["dataType"] not in TEXT_TYPES:
            continue
        inspected = inspect_numeric_text([rows[int(i)].get(name) for i in train_indices])
        # Raising the category budget deliberately retains the user's existing
        # equality encoding. This inference only recovers otherwise lost ranges.
        if not inspected["eligible"] or inspected["distinctCount"] <= category_limit:
            continue
        if target_rows is rows:
            target_rows = [dict(row) for row in rows]
        inferred.add(name)
        for source, target in zip(rows, target_rows):
            target[name] = parse_numeric_decimal(source.get(name))
        diagnostics.append({"column": name, **inspected, "fitSource": "TRAIN_ONLY",
                            "encoding": "NUMERIC_TEXT_RANGE", "originalValuesPreserved": True})
    metadata = [{**column, "dataType": "NUMBER"} if column["name"] in inferred else column for column in columns]
    feature_rows = target_rows
    if inferred:
        # sklearn uses float32. Saturating only its feature view preserves the
        # branch ordering of Oracle BINARY_FLOAT infinities for extreme holdout
        # values, without changing exact target classes or original raw values.
        maximum = float(np.finfo(np.float32).max)
        feature_rows = [dict(row) for row in target_rows]
        for row in feature_rows:
            for name in inferred:
                value = row[name]
                if value is not None:
                    row[name] = max(-maximum, min(maximum, float(value)))
    return target_rows, feature_rows, metadata, inferred, diagnostics


def annotate_numeric_text(node, inferred):
    if "conditions" in node:
        return {**node, "conditions": [annotate_numeric_text(child, inferred) for child in node["conditions"]]}
    return {**node, "numericText": True} if node.get("column") in inferred else node
