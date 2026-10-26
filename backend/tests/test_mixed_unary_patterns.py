import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse

from backend.services.mixed_pattern_algorithm import analyze_pattern_rows, evaluate_pattern_predicate
from backend.services.mixed_unary_patterns import SparseUnaryPatterns, select_condition_patterns


class SparseUnaryTests(unittest.TestCase):
    def test_independent_single_condition_adds_validated_violation_rule_without_another_tree(self):
        rows = [{"A":str(i % 2), "B":str((i % 2) ^ (i % 200 == 0)), "OUTCOME":str(i % 2)} for i in range(2000)]
        columns = [{"name":name,"dataType":"VARCHAR2"} for name in ("A","B","OUTCOME")]
        options = {"targetColumns":["OUTCOME"],"treeMaxDepth":1,"minConfidence":.98}
        with patch.object(SparseUnaryPatterns,"candidates",return_value=iter(())):
            baseline = analyze_pattern_rows(rows,columns,options)
        self.assertTrue(all("B" not in rule["expression"] for rule in baseline["rules"]))
        result = analyze_pattern_rows(rows,columns,options)
        additions = [rule for rule in result["rules"] if rule.get("candidateMethod") == "SPARSE_UNARY_FREQUENCY" and rule["predicate"].get("column") == "B"]
        self.assertTrue(additions)
        detected = {i for rule in additions for i,row in enumerate(rows) if evaluate_pattern_predicate(rule["predicate"],row) and not evaluate_pattern_predicate(rule["resultPredicate"],row)}
        self.assertEqual(detected,set(range(0,2000,200)))
        for rule in additions:
            self.assertGreaterEqual(rule["confidence"],.98)
            self.assertGreaterEqual(rule["validation"]["confidence"],.9)
        self.assertEqual(result["metrics"]["fittedTargetCount"],baseline["metrics"]["fittedTargetCount"])
        self.assertEqual(result["metrics"]["unaryFrequency"]["fitSource"],"TRAIN_ONLY")

    def test_validation_does_not_choose_consequent_and_missing_targets_stay_in_denominator(self):
        design=sparse.csr_matrix(np.asarray([[1,0]]*50+[[0,1]]*50+[[1,0]]*20+[[0,1]]*20,dtype=np.float32))
        features=[{"kind":"category","column":"GROUP","category":value} for value in ("A","B")]
        labels=np.asarray([0]*49+[-1]+[1]*50+[1]*20+[0]*20,dtype=np.int32)
        miner=SparseUnaryPatterns(design,features,np.arange(100),np.arange(100,140),2,32)
        rules=list(miner.candidates("TARGET",labels,2,2,0))
        first=next(rule for rule in rules if rule["feature"]["category"] == "A")
        self.assertEqual((first["classIndex"],first["conditionCount"],first["supportCount"]),(0,50,49))
        self.assertEqual((first["validationCount"],first["validationSupport"]),(20,0))
        self.assertEqual(list(miner.candidates("GROUP",labels,2,2,0)),[])
        self.assertEqual(list(miner.candidates("TARGET",labels,2,80,0)),[])
        self.assertEqual(list(miner.candidates("TARGET",labels,2,2,.9)),[])

    def test_sparse_work_is_capped_by_existing_rule_and_feature_limits(self):
        rng=np.random.default_rng(12)
        design=sparse.random(10000,400,density=.02,format="csr",random_state=rng,dtype=np.float32)
        design.data[:]=1
        features=[{"kind":"category","column":f"F{i}","category":"yes"} for i in range(400)]
        for rule_limit,expected in ((64,128),(4,16)):
            miner=SparseUnaryPatterns(design,features,np.arange(7500),np.arange(7500,10000),2,rule_limit)
            self.assertEqual(len(miner.indices),expected)
            self.assertTrue(sparse.issparse(miner.train_design))
            self.assertEqual(miner.train_design.shape,(7500,expected))
            self.assertFalse(miner.metrics()["denseSampleMatrix"])

    def pattern(self,identifier,predicate,method="COLUMN_TREE",confidence=.99):
        return {"ruleId":identifier,"predicate":predicate,"resultPredicate":{"column":"Y","operator":"=","value":"ok"},
                "candidateMethod":method,"confidence":confidence,"supportCount":100,"lift":2}

    def test_extra_clean_candidates_cannot_evict_the_original_tree_budget(self):
        atom={"column":"A","operator":"=","value":"x"}
        original=self.pattern("old",atom)
        extra=self.pattern("extra",{"column":"B","operator":"=","value":"b"},"SPARSE_UNARY_FREQUENCY",1)
        self.assertEqual(select_condition_patterns([original,extra],1),[original])
        self.assertEqual(len(select_condition_patterns([original,extra],2)),2)

    def test_simpler_rule_replaces_only_logically_covered_same_results(self):
        atom={"column":"A","operator":"=","value":"x"}
        other={"column":"B","operator":"=","value":"b"}
        narrow=self.pattern("narrow",{"operator":"AND","conditions":[atom,other]})
        broad=self.pattern("broad",atom,"SPARSE_UNARY_FREQUENCY")
        self.assertEqual(select_condition_patterns([narrow,broad],1),[broad])
        union=self.pattern("union",{"operator":"OR","conditions":[atom,other]})
        self.assertEqual(select_condition_patterns([union,broad],1),[union])
        broad["resultPredicate"]={"column":"Y","operator":"=","value":"different"}
        self.assertEqual(select_condition_patterns([narrow,broad],1),[narrow])

    def test_noise_and_user_exclusions_do_not_bypass_existing_quality_settings(self):
        rng=np.random.default_rng(77)
        rows=[{"A":str(rng.integers(4)),"B":str(rng.integers(4)),"Y":str(rng.integers(4))} for _ in range(2000)]
        columns=[{"name":name,"dataType":"VARCHAR2"} for name in ("A","B","Y")]
        result=analyze_pattern_rows(rows,columns,{"targetColumns":["Y"],"excludeColumns":["B"]})
        self.assertEqual(result["rules"],[])
        self.assertEqual(result["metrics"]["unaryFrequency"]["featureCount"],8)


class UnaryStoredPipelineTests(unittest.TestCase):
    def test_real_registered_discovery_saves_unary_ast_and_detects_later_varchar_errors(self):
        import json
        from backend.services import mixed_xai_service as xai, mixed_pattern_service as patterns
        from backend.tests.test_mixed_continuous_pipeline import UploadedNumericConnection
        from backend.tests.test_mixed_pattern_service import PAYLOAD
        names=("GROUP_CODE","REGION","FILE_ROW_NO","X","Y")
        rows=[(f"Y{i % 2}",f"R{i % 2}",i+1,f"B{(i % 2) ^ (i % 200 == 0)}","1") for i in range(2000)]
        conn=UploadedNumericConnection(rows)
        self.addCleanup(conn.db.close)
        xai.discover(conn,{**PAYLOAD,"targetColumns":["GROUP_CODE"],"treeMaxDepth":1,"minConfidence":.98,"continuousEnabled":False})
        stored=conn.records(patterns.RULE_TABLE)
        selected=[rule for rule in stored if json.loads(rule["CONDITION_JSON"]).get("column") == "X"]
        self.assertTrue(selected)
        later=[("Y0","R0",2001,"B1","1"),(None,"R1",2002,"B1","1")]
        conn.db.executemany("INSERT INTO SOURCE_UPLOADED VALUES (?,?,?,?,?)",later)
        conn.db.commit()
        originals={rule["RULE_ID"]:(rule["CONDITION_JSON"],rule["RESULT_JSON"],rule["VALIDATION_JSON"]) for rule in selected}
        xai.detect(conn,{**PAYLOAD,"maxViolationRows":200})
        full=[dict(zip(names,row)) for row in rows+later]
        previews=conn.records(patterns.VIOLATION_TABLE)
        for rule in conn.records(patterns.RULE_TABLE):
            if rule["RULE_ID"] not in originals:
                continue
            self.assertEqual((rule["CONDITION_JSON"],rule["RESULT_JSON"],rule["VALIDATION_JSON"]),originals[rule["RULE_ID"]])
            predicate=json.loads(rule["CONDITION_JSON"]); consequent=json.loads(rule["RESULT_JSON"])
            expected={str(row["FILE_ROW_NO"]) for row in full if evaluate_pattern_predicate(predicate,row) and not evaluate_pattern_predicate(consequent,row)}
            self.assertEqual(rule["VIOLATION_COUNT"],len(expected))
            self.assertEqual({row["CASE_ID"] for row in previews if row["RULE_ID"] == rule["RULE_ID"]},expected)
        self.assertTrue({"2001","2002"} <= {row["CASE_ID"] for row in previews})
