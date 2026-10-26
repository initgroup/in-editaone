"""Quick Edit must reject unsuitable input before any database mutation."""
import io
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from backend.routers import M02001 as upload


class QuickEditPreflightTests(unittest.TestCase):
    def inspect(self, text, *, has_header="Y", delimiter=","):
        stream = io.BytesIO(text.encode("utf-8"))
        result = upload.inspect_quick_edit_upload(stream, "source.csv", "csv", delimiter, "", has_header, "utf-8")
        self.assertFalse(stream.closed)
        self.assertEqual(stream.tell(), 0)
        return result

    def test_empty_one_column_and_too_few_rows_are_actionable(self):
        for text, expected in (("", {"TOO_FEW_COLUMNS", "TOO_FEW_ROWS"}),
                               ("A\n1\n", {"TOO_FEW_COLUMNS", "TOO_FEW_ROWS"}),
                               ("A,B\n1,2\n", {"TOO_FEW_ROWS"})):
            with self.subTest(text=text):
                result = self.inspect(text)
                self.assertFalse(result["valid"])
                self.assertEqual({issue["code"] for issue in result["issues"]}, expected)
                self.assertTrue(result["rowCountExact"])

    def test_exact_threshold_excludes_header_and_blank_rows(self):
        for count in (31, 32):
            result = self.inspect("A,B\n\n" + "\n".join(f"group,{i}" for i in range(count)))
            self.assertEqual(result["valid"], count == 32)
            self.assertEqual(result["checkedDataRows"], count)
        result = self.inspect("\n".join(f"group,{i}" for i in range(32)), has_header="N")
        self.assertTrue(result["valid"])

    def test_three_row_grouped_heading_is_rejected_even_with_many_rows(self):
        text = "Category,Detail,2018,2018\nCategory,Detail,Income,Income\nCategory,Detail,Low,High\n"
        result = self.inspect(text + "\n".join(f"Group,Area{i},10,20" for i in range(40)))
        self.assertFalse(result["valid"])
        self.assertEqual(result["issues"], [{"code": "MULTI_ROW_HEADER", "headerRows": 3}])

    def test_duplicate_labels_alone_do_not_reject_valid_data(self):
        result = self.inspect("Category,Detail,Value,Value\n" + "\n".join(f"Group,Area{i},10,20" for i in range(40)))
        self.assertTrue(result["valid"])

    def test_wrong_delimiter_width_mismatch_and_large_cells_are_rejected(self):
        wrong_delimiter = self.inspect("A;B\n" + "x;y\n" * 32)
        self.assertEqual(wrong_delimiter["issues"][0]["code"], "TOO_FEW_COLUMNS")
        mismatch = self.inspect("A,B\nx,y,z\n" + "x,y\n" * 32)
        self.assertEqual(mismatch["issues"][0]["code"], "ROW_WIDTH")
        oversized = self.inspect("A,B\n" + "x," + "가" * 1334 + "\n" + "x,y\n" * 32)
        self.assertEqual(oversized["issues"][0]["code"], "CELL_SIZE")

    def test_probe_is_bounded_and_reports_that_count_is_not_exact(self):
        result = self.inspect("A,B\n" + "x,y\n" * 10000)
        self.assertTrue(result["valid"])
        self.assertEqual(result["checkedDataRows"], 64)
        self.assertFalse(result["rowCountExact"])

    def test_staged_route_uses_session_ownership_without_database_access(self):
        upload_id = "b" * 32
        with tempfile.TemporaryDirectory() as directory, patch.object(upload, "UPLOAD_STAGING_DIRECTORY", Path(directory)), \
                patch.object(upload, "get_request_user_id", return_value=7), \
                patch.object(upload, "get_target_db_connection", side_effect=AssertionError("No DB access allowed")):
            data_path, _ = upload.get_staging_paths(upload_id)
            content = b"A,B\n" + b"x,y\n" * 32
            data_path.write_bytes(content)
            upload.write_staged_upload_metadata(upload_id, {
                "userId": "7", "fileName": "source.csv", "createdAt": time.time(), "expectedSize": len(content),
            })
            result = upload.preflight_staged_quick_edit_upload(object(), upload_id, "csv", ",", "", "Y", "utf-8")
            self.assertTrue(result["valid"])
            with patch.object(upload, "get_request_user_id", return_value=8), self.assertRaises(HTTPException) as denied:
                upload.preflight_staged_quick_edit_upload(object(), upload_id, "csv", ",", "", "Y", "utf-8")
            self.assertEqual(denied.exception.status_code, 404)

    def test_corrupt_excel_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            upload.inspect_quick_edit_upload(io.BytesIO(b"not an xlsx"), "bad.xlsx", "excel", ",", "", "Y", "auto")
        self.assertEqual(raised.exception.status_code, 400)
