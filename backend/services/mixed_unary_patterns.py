"""Bounded frequency candidates reusing the mixed model's sparse encoding."""
import numpy as np
from scipy import sparse


class SparseUnaryPatterns:
    # Fixed work bound, further reduced by the caller's existing rule/feature caps.
    FEATURE_LIMIT = 128

    def __init__(self, matrix, features, train, validation, min_count, rule_limit):
        self.train, self.validation = train, validation
        self.features = features
        self.indices = []
        self.examined = 0
        if matrix is None:
            return
        indices = [i for i, feature in enumerate(features) if feature["kind"] == "category"]
        if not indices:
            return
        design = matrix[:, indices].tocsr()
        counts = np.asarray(design[train].sum(axis=0)).ravel()
        ranked = sorted((i for i in range(len(indices)) if counts[i] >= min_count),
                        key=lambda i: (-counts[i], indices[i]))
        retained = ranked[:min(self.FEATURE_LIMIT, rule_limit * 4)]
        self.indices = [indices[i] for i in retained]
        self.train_design = design[train][:, retained].tocsr()
        self.validation_design = design[validation][:, retained].tocsr()
        self.train_counts = np.asarray(self.train_design.sum(axis=0)).ravel()
        self.validation_counts = np.asarray(self.validation_design.sum(axis=0)).ravel()

    @staticmethod
    def _counts(design, labels, class_count):
        valid = np.flatnonzero(labels >= 0)
        encoded = sparse.csr_matrix((np.ones(len(valid), dtype=np.float32), (valid, labels[valid])),
                                    shape=(len(labels), class_count))
        return (design.T @ encoded).toarray()

    def candidates(self, name, labels, class_count, min_leaf, min_impurity):
        if not self.indices:
            return
        training = labels[self.train]
        counts = self._counts(self.train_design, training, class_count)
        totals = np.bincount(training[training >= 0], minlength=class_count)
        total = int(totals.sum())
        if total == 0:
            return
        # Honor the same min-leaf and impurity settings as the existing tree.
        branch = counts.sum(axis=1)
        other = total - branch
        complement = totals - counts
        impurity_gain = (np.sum(counts ** 2, axis=1) / np.maximum(branch, 1)
                         + np.sum(complement ** 2, axis=1) / np.maximum(other, 1)) / total - np.sum((totals / total) ** 2)
        eligible = [i for i, index in enumerate(self.indices) if self.features[index]["column"] != name
                    and branch[i] >= min_leaf and other[i] >= min_leaf and impurity_gain[i] >= min_impurity]
        if not eligible:
            return
        expected = counts.argmax(axis=1)  # Training only; validation never chooses a consequent.
        checked = self._counts(self.validation_design, labels[self.validation], class_count)
        for i in eligible:
            self.examined += 1
            cls = int(expected[i])
            yield {"feature": self.features[self.indices[i]], "featureIndex": self.indices[i], "classIndex": cls,
                   "conditionCount": int(self.train_counts[i]), "supportCount": int(counts[i, cls]),
                   "validationCount": int(self.validation_counts[i]), "validationSupport": int(checked[i, cls])}

    def metrics(self):
        return {"method": "SPARSE_UNARY_FREQUENCY", "featureCount": len(self.indices),
                "featureLimit": self.FEATURE_LIMIT, "examinedCandidateCount": self.examined,
                "fitSource": "TRAIN_ONLY", "denseSampleMatrix": False}


def _implies(predicate, atom):
    if predicate == atom:
        return True
    children = predicate.get("conditions", [])
    if predicate.get("operator") == "AND":
        return any(_implies(child, atom) for child in children)
    if predicate.get("operator") == "OR" and children:
        return all(_implies(child, atom) for child in children)
    return False


def select_condition_patterns(rules, limit):
    """Preserve the original top-tree budget and its violation coverage.

    A unary rule may replace a same-consequent tree rule only if the saved tree
    predicate logically implies the unary predicate, independent of this sample.
    Extra candidates fill vacant slots; they never evict the existing selection.
    """
    rank = lambda rule: (-rule["confidence"], -rule["supportCount"], -rule["lift"], rule["ruleId"])
    selected = sorted((rule for rule in rules if rule["candidateMethod"] == "COLUMN_TREE"), key=rank)[:limit]
    extra = []
    for unary in sorted((rule for rule in rules if rule["candidateMethod"] == "SPARSE_UNARY_FREQUENCY"), key=rank):
        replaced = [rule for rule in selected if rule["resultPredicate"] == unary["resultPredicate"]
                    and _implies(rule["predicate"], unary["predicate"])]
        if replaced:
            selected = [rule for rule in selected if rule not in replaced] + [unary]
        else:
            extra.append(unary)
    selected.extend(extra[:max(0, limit - len(selected))])
    return sorted(selected, key=rank)
