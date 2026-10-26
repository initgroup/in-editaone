"""File-only demo: full-source sampling, early validation and real rule discovery."""
import io
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, Response, UploadFile
from starlette.requests import Request

from backend.routers import M00002
from backend.services import simple_editing as service

ROOT = Path(__file__).resolve().parents[2]


def csv_file(count=40, header="Label,Amount"):
    return io.BytesIO((header + "\n" + "\n".join(f"group,{i}" for i in range(count))).encode())


class SimpleEditingTests(unittest.TestCase):
    def test_demo_session_uses_verified_server_identity_without_target_db(self):
        request = Request({"type": "http", "method": "GET", "path": "/api/M00002/session",
                           "headers": [(b"x-login-user-id", b"7"), (b"x-login-role", b"ADMIN")], "query_string": b"userId=7"})
        with self.assertRaises(HTTPException) as caught:
            M00002.session(request, Response())
        self.assertEqual(caught.exception.status_code, 401)
        request.state.auth_user = {"userId": 7}
        response = Response()
        result = M00002.session(request, response)
        self.assertEqual(result["user"], {"userId": 7})
        self.assertGreaterEqual(result["sessionTtlSeconds"], 300)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_reservoir_covers_entire_source_and_changes_with_seed(self):
        samples = []
        for seed in (17, 71):
            stream = csv_file(50000)
            rows, columns, labels, total, _ = service.read_sample(stream, "input.csv", seed=seed)
            self.assertEqual(total, 50000)
            self.assertEqual(len(rows), 10000)
            self.assertEqual(columns[0]["DATA_TYPE"], "VARCHAR2")
            self.assertEqual(labels["C002"], "Amount")
            numbers = {int(row["C002"]) for row in rows}
            self.assertGreater(max(numbers), 49000)
            self.assertTrue(all(row["__source_row__"] == int(row["C002"]) + 1 for row in rows))
            for quarter in range(4):
                self.assertTrue(2200 < sum(quarter * 12500 <= value < (quarter + 1) * 12500 for value in numbers) < 2800)
            samples.append(numbers)
            self.assertFalse(stream.closed)
            self.assertEqual(stream.tell(), 0)
        self.assertNotEqual(*samples)

    def test_exact_minimum_excludes_header_and_all_small_file_rows_are_preserved(self):
        with self.assertRaises(HTTPException) as caught:
            service.inspect_file(csv_file(31), "input.csv")
        self.assertEqual(caught.exception.detail["code"], "TOO_FEW_ROWS")
        self.assertIn("31", caught.exception.detail["message"])
        rows, _, _, total, _ = service.read_sample(csv_file(32), "input.csv", seed=42)
        self.assertEqual(total, 32)
        self.assertEqual({row["C002"] for row in rows}, {str(i) for i in range(32)})

    def test_invalid_headers_width_and_large_cells_are_actionable(self):
        examples = [("A,A\n", "HEADER"), ("A,\n", "HEADER"), ("1,2\n", "HEADER"),
                    ("A\n", "COLUMN_COUNT"), ("A,B\nA,B\n", "HEADER"),
                    ("A,B\nx,y,z\n", "ROW_WIDTH"), ("A,B\nx," + "가" * 1334 + "\n", "CELL_SIZE")]
        for content, code in examples:
            with self.subTest(code=code), self.assertRaises(HTTPException) as caught:
                service.inspect_file(io.BytesIO(content.encode("utf-8")), "input.csv")
            self.assertEqual(caught.exception.detail["code"], code)

    def test_tsv_korean_headers_and_whitespace_data_are_preserved(self):
        content = "이름\t금액\n" + " 가 \t12\n" * 40
        rows, _, labels, _, _ = service.read_sample(io.BytesIO(content.encode()), "한글.tsv", seed=0)
        self.assertEqual(labels["C001"], "이름")
        self.assertEqual(rows[0]["C001"], " 가 ")

    def test_file_and_source_limits_reject_instead_of_prefix_truncation(self):
        with patch.object(service, "MAX_FILE_BYTES", 10), self.assertRaises(HTTPException) as caught:
            service.inspect_file(csv_file(), "input.csv")
        self.assertEqual(caught.exception.status_code, 413)
        with patch.object(service, "MAX_SOURCE_ROWS", 35), self.assertRaises(HTTPException) as caught:
            service.inspect_file(csv_file(), "input.csv")
        self.assertEqual(caught.exception.detail["code"], "SOURCE_ROWS")
        with patch.object(service, "MAX_SAMPLE_BYTES", 1), self.assertRaises(HTTPException) as caught:
            service.inspect_file(csv_file(), "input.csv")
        self.assertEqual(caught.exception.detail["code"], "SAMPLE_MEMORY")
        for filename in ("input.exe", "broken.xlsx"):
            with self.assertRaises(HTTPException):
                service.inspect_file(csv_file(), filename)
        from zipfile import ZipFile
        malformed = io.BytesIO()
        with ZipFile(malformed, "w") as archive:
            archive.writestr("wrong.xml", "not a workbook")
        with self.assertRaises(HTTPException) as caught:
            service.inspect_file(malformed, "broken.xlsx")
        self.assertEqual(caught.exception.status_code, 400)

    def test_column_limit_is_nonblocking_and_preserves_only_first_100_columns(self):
        for count in (99, 100, 105):
            content = ",".join(f"Field{i}" for i in range(1, count + 1)) + "\n"
            content += (",".join(str(i) for i in range(1, count + 1)) + "\n") * 40
            data = service.inspect_file(io.BytesIO(content.encode()), "wide.csv")["data"]
            self.assertEqual(data["sourceColumns"], count)
            self.assertEqual(data["columns"], min(count, 100))
            self.assertEqual(data["omittedColumns"], max(count - 100, 0))
            rows, _, labels, _, _ = service.read_sample(io.BytesIO(content.encode()), "wide.csv", seed=17)
            if count >= 100:
                self.assertEqual(labels["C100"], "Field100")
                self.assertEqual(rows[0]["C100"], "100")
            self.assertNotIn("C101", rows[0])

    def test_excluded_columns_do_not_block_validation_or_inflate_retained_sample(self):
        header = [f"Field{i}" for i in range(100)] + [""]
        content = ",".join(header) + "\n" + (",".join(["x"] * 100 + ["가" * 2000]) + "\n") * 40
        result = service.inspect_file(io.BytesIO(content.encode()), "wide.csv")["data"]
        self.assertEqual(result["omittedColumns"], 1)
        content = ",".join(header[:100]) + "\n" + (",".join(["x"] * 100) + "\n") * 10000
        result = service.inspect_file(io.BytesIO(content.encode()), "wide.csv")["data"]
        self.assertEqual(result["sampleRows"], 10000)

    def test_wide_csv_and_excel_execute_real_discovery_with_column_scope(self):
        import csv
        from openpyxl import Workbook
        with (ROOT / "simple-edit/sample.csv").open(encoding="utf-8-sig", newline="") as source:
            original = list(csv.reader(source))
        source_rows = [original[0] + [f"Extra{i}" for i in range(97)]]
        source_rows.extend(row + ["constant"] * 97 for row in original[1:])
        csv_stream = io.StringIO(newline="")
        csv.writer(csv_stream).writerows(source_rows)
        workbook = Workbook()
        for row in source_rows:
            workbook.active.append(row)
        excel_stream = io.BytesIO()
        workbook.save(excel_stream)
        for stream, filename in ((io.BytesIO(csv_stream.getvalue().encode()), "wide.csv"), (excel_stream, "wide.xlsx")):
            with patch.object(service.secrets, "randbits", return_value=17):
                result = service.analyze_file(stream, filename)["data"]
            self.assertEqual(result["sourceColumns"], 105)
            self.assertEqual(result["columns"], 100)
            self.assertEqual(result["omittedColumns"], 5)
            self.assertTrue(result["rules"]["FORMULA"])
            self.assertTrue(result["rules"]["CONDITION"])

    def test_excel_reads_actual_cells_even_when_dimension_is_a1(self):
        from openpyxl import Workbook
        from zipfile import ZipFile
        workbook = Workbook()
        workbook.active.append(["Kind", "Value"])
        for i in range(40):
            workbook.active.append(["A", i])
        original = io.BytesIO()
        workbook.save(original)
        broken = io.BytesIO()
        with ZipFile(original) as source, ZipFile(broken, "w") as target:
            for info in source.infolist():
                content = source.read(info.filename)
                if info.filename == "xl/worksheets/sheet1.xml":
                    content = content.replace(b'ref="A1:B41"', b'ref="A1"')
                target.writestr(info, content)
        result = service.inspect_file(broken, "input.xlsx")
        self.assertEqual(result["data"]["sourceRows"], 40)
        self.assertEqual(result["data"]["columns"], 2)

    def test_preflight_never_runs_model_and_requires_server_session(self):
        request = Request({"type": "http", "headers": [], "method": "POST", "path": "/api/M00002/preflight"})
        denied_file = UploadFile(csv_file(), filename="input.csv")
        with self.assertRaises(HTTPException) as caught:
            M00002.preflight(request, denied_file)
        self.assertEqual(caught.exception.status_code, 401)
        self.assertTrue(denied_file.file.closed)
        with patch.object(M00002, "get_request_user_id", return_value=7), \
             patch.object(service, "analyze_pattern_rows", side_effect=AssertionError("No model during preflight")):
            result = M00002.preflight(request, UploadFile(csv_file(), filename="input.csv"))
        self.assertEqual(result["data"]["sourceRows"], 40)

    def test_actual_demo_file_discovers_both_types_with_fresh_seeds(self):
        responses = []
        for seed in (17, 71):
            with (ROOT / "simple-edit/sample.csv").open("rb") as stream, patch.object(service.secrets, "randbits", return_value=seed):
                result = service.analyze_file(stream, "sample.csv")["data"]
            self.assertEqual(result["sourceRows"], 2400)
            self.assertEqual(result["sampleRows"], 2400)
            self.assertEqual(result["source"], "MIXED_PATTERN")
            self.assertEqual(result["algorithm"], "MIXED_PATTERN_TREE")
            for family in ("FORMULA", "CONDITION"):
                self.assertTrue(1 <= len(result["rules"][family]) <= 5, (family, result["counts"]))
                for rule in result["rules"][family]:
                    self.assertEqual(rule["source"], "MIXED_PATTERN")
                    self.assertGreaterEqual(rule["validationConfidence"], .9)
                    self.assertGreater(rule["validationRows"], 0)
                    self.assertEqual(rule["detail"]["validationStats"]["applied"], rule["validationRows"])
                    self.assertAlmostEqual(rule["detail"]["validationStats"]["matched"] / rule["validationRows"], rule["validationConfidence"])
                    self.assertEqual(rule["detail"]["cohort"], "ANALYZED_SAMPLE")
                    self.assertEqual(rule["detail"]["scannedRows"], result["sampleRows"])
                    self.assertGreater(rule["detail"]["stats"]["different"], 0)
                    self.assertGreaterEqual(rule["detail"]["stats"]["applied"], rule["validationRows"])
                    self.assertLessEqual(len(rule["detail"]["rows"]), 120)
                    self.assertNotRegex(rule["result"], r"C00\d")
            self.assertTrue(any("공급가액" in rule["result"] for rule in result["rules"]["FORMULA"]))
            responses.append(result)
        self.assertNotEqual(responses[0]["sampleSeed"], responses[1]["sampleSeed"])

    def test_detection_scans_only_the_full_random_sample_not_unselected_source_rows(self):
        rule = {"ruleId":"formula", "resultKind":"FORMULA", "resultColumn":"C003", "confidence":1., "supportCount":100,
                "validation":{"confidence":1., "conditionCount":2500},
                "predicate":{"operator":"NOT_NULL","column":"C001","numericText":True},
                "resultPredicate":{"operator":"WITHIN_TOLERANCE","column":"C003","numericText":True,
                    "expression":{"operator":"ADD","left":{"column":"C001","numericText":True},"right":{"column":"C002","numericText":True}},
                    "absoluteTolerance":.01,"relativeTolerance":0}}
        captured = []

        def discover(rows, columns, options):
            captured.extend(rows)
            return {"algorithm":"MIXED_PATTERN_TREE", "rules":[rule], "rows":[{"rowIndex":i,"partition":"VALIDATION" if i % 4 == 0 else "TRAIN"} for i in range(len(rows))], "metrics":{}}

        content = "A,B,Total\n" + "\n".join(f"{i},1,{i + 2}" for i in range(15000))
        with patch.object(service, "analyze_pattern_rows", side_effect=discover), patch.object(service.secrets, "randbits", return_value=17):
            result = service.analyze_file(io.BytesIO(content.encode()), "large.csv")["data"]
        details = result["rules"]["FORMULA"][0]["detail"]
        self.assertEqual(result["detectionScope"], "ANALYZED_SAMPLE")
        self.assertEqual(result["sourceRows"], 15000)
        self.assertEqual(result["sampleRows"], 10000)
        self.assertEqual(details["scannedRows"], 10000)
        self.assertEqual(details["stats"]["different"], 10000)
        self.assertEqual(details["validationStats"]["different"], 2500)
        selected_rows = {row["__source_row__"] for row in captured}
        self.assertTrue(all(row["sourceRow"] in selected_rows for row in details["rows"]))
        self.assertGreater(max(row["sourceRow"] for row in details["rows"]), 10000)

    def test_server_preserves_diverse_relations_before_the_five_rule_display_cap(self):
        proposals = [("C003","C001","C002","ADD"), ("C001","C003","C002","SUBTRACT"),
                     ("C002","C003","C001","SUBTRACT")]
        proposals.extend((f"C00{i}","C001","C002","ADD") for i in range(4,8))
        rules = [{"ruleId":str(i),"resultKind":"FORMULA","resultColumn":target,"confidence":1.,"supportCount":1000-i,
                  "predicate":{"operator":"NOT_NULL","column":left,"numericText":True},
                  "resultPredicate":{"operator":"WITHIN_TOLERANCE","column":target,"numericText":True,
                      "expression":{"operator":operator,"left":{"column":left,"numericText":True},"right":{"column":right,"numericText":True}},
                      "absoluteTolerance":.01,"relativeTolerance":0}}
                 for i,(target,left,right,operator) in enumerate(proposals)]
        content = "A,B,C,D,E,F,G\n" + "1,2,4,4,4,4,4\n" * 40
        result = {"algorithm":"MIXED_PATTERN_TREE","rules":rules,"rows":[{"rowIndex":i,"partition":"VALIDATION"} for i in range(40)],"metrics":{}}
        with patch.object(service,"analyze_pattern_rows",return_value=result):
            data=service.analyze_file(io.BytesIO(content.encode()),"relations.csv")["data"]
        self.assertEqual([rule["id"] for rule in data["rules"]["FORMULA"]],["0","3","4","5","6"])
        self.assertEqual(data["counts"]["FORMULA"],7)

    def test_clean_rules_are_removed_before_top_limit_for_both_families(self):
        rules = []
        for kind in ("FORMULA", "VALUE"):
            for i in range(12):
                clean = i < 6
                result = {"operator": "=", "column": "C003", "value": "3" if clean else "4"}
                if kind == "FORMULA":
                    result = {"operator": "WITHIN_TOLERANCE", "column": "C003", "numericText": True,
                              "expression": {"operator": "ADD", "left": {"column": "C001", "numericText": True},
                                             "right": {"value": 2 if clean else 3}},
                              "absoluteTolerance": .01, "relativeTolerance": 0}
                rules.append({"ruleId": f"{kind}{i:02}", "resultKind": kind, "resultColumn": "C003",
                              "confidence": 1 if clean else .95, "supportCount": 100 - i,
                              "predicate": {"operator": "NOT_NULL", "column": "C001"}, "resultPredicate": result})
        analysis = {"algorithm": "MIXED_PATTERN_TREE", "rules": rules, "rows": [], "metrics": {}}
        with patch.object(service, "analyze_pattern_rows", return_value=analysis):
            data = service.analyze_file(io.BytesIO(b"A,B,Total\n" + b"1,2,3\n" * 40), "rules.csv")["data"]
            self.assertEqual(data["counts"], {"FORMULA": 6, "CONDITION": 6})
            for family, prefix in (("FORMULA", "FORMULA"), ("CONDITION", "VALUE")):
                self.assertEqual([rule["id"] for rule in data["rules"][family]], [f"{prefix}{i:02}" for i in range(6, 11)])
                self.assertTrue(all(rule["detail"]["stats"]["different"] == 40 for rule in data["rules"][family]))
            analysis["rules"] = [rule for rule in rules if int(rule["ruleId"][-2:]) < 6]
            clean_data = service.analyze_file(io.BytesIO(b"A,B,Total\n" + b"1,2,3\n" * 40), "clean.csv")["data"]
        self.assertEqual(clean_data["rules"], {"FORMULA": [], "CONDITION": []})
        self.assertEqual(clean_data["counts"], {"FORMULA": 0, "CONDITION": 0})
        self.assertEqual(clean_data["discoveredCounts"], {"FORMULA": 6, "CONDITION": 6})

    def test_unrelated_data_does_not_invent_formulas(self):
        import random
        rng = random.Random(42)
        content = "A,B,C\n" + "\n".join(",".join(str(rng.uniform(10, 10000)) for _ in range(3)) for _ in range(250))
        with patch.object(service.secrets, "randbits", return_value=17):
            result = service.analyze_file(io.BytesIO(content.encode()), "random.csv")["data"]
        self.assertEqual(result["rules"]["FORMULA"], [])

    def test_body_limits_for_both_routes_with_or_without_content_length(self):
        from main import _GeminiRequestBodyLimitMiddleware

        async def run(path, with_length):
            messages, reached = [], []
            async def app(scope, receive, send):
                reached.append(True)
                await receive()
                await send({"type": "http.response.start", "status": 200, "headers": []})
                await send({"type": "http.response.body", "body": b"ok"})
            async def receive():
                return {"type": "http.request", "body": b"x" * (21 * 1024 * 1024), "more_body": False}
            async def send(message):
                messages.append(message)
            scope = {"type": "http", "method": "POST", "path": path,
                     "headers": [(b"content-length", str(21 * 1024 * 1024).encode())] if with_length else []}
            await _GeminiRequestBodyLimitMiddleware(app)(scope, receive, send)
            self.assertEqual(messages[0]["status"], 413)
            if with_length:
                self.assertFalse(reached)
        for path in ("/api/M00002/preflight", "/api/M00002/analyze"):
            for with_length in (True, False):
                # This ASGI fake never yields I/O; avoid a Windows loop socketpair
                # because the offline harness intentionally blocks all networking.
                coroutine = run(path, with_length)
                with self.assertRaises(StopIteration):
                    coroutine.send(None)
