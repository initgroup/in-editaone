import io
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from fastapi import HTTPException

from backend.database_helper import SqlLoader
from backend.routers import M02001


class FakeUploadCursor:
    def __init__(self):
        self.batch_sizes = []

    def executemany(self, _sql, rows):
        self.batch_sizes.append(len(rows))


class FakeUploadConnection:
    def __init__(self):
        self.commit_count = 0

    def commit(self):
        self.commit_count += 1


class FakeDirectPathConnection(FakeUploadConnection):
    def __init__(self):
        super().__init__()
        self.loads = []

    def direct_path_load(self, schema_name, table_name, column_names, data, *, batch_size):
        self.loads.append((schema_name, table_name, column_names, list(data), batch_size))


class M02001UploadOptimizationTests(unittest.TestCase):
    def test_excel_single_cell_dimension_does_not_truncate_real_data(self):
        from openpyxl import Workbook

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["GROUP_CODE", "VALUE", "TOTAL"])
        worksheet.append(["A", "10", "20"])
        worksheet.append(["B", "15", "30"])
        original = io.BytesIO()
        workbook.save(original)
        workbook.close()
        stream = io.BytesIO()
        with ZipFile(original) as source, ZipFile(stream, "w") as destination:
            for entry in source.infolist():
                content = source.read(entry.filename)
                if entry.filename == "xl/worksheets/sheet1.xml":
                    content = content.replace(b'<dimension ref="A1:C3"', b'<dimension ref="A1"')
                    self.assertIn(b'<dimension ref="A1"', content)
                destination.writestr(entry, content)

        preview_columns, preview_rows, _ = M02001.read_upload_preview(
            stream, "export.xlsx", "excel", ",", "", "Y", "auto", 20,
        )
        self.assertEqual(preview_columns, ["GROUP_CODE", "VALUE", "TOTAL"])
        self.assertEqual(preview_rows, [["A", "10", "20"], ["B", "15", "30"]])
        columns, width, header_width = M02001.inspect_upload_schema(
            stream, "export.xlsx", "excel", ",", "", "Y", None,
        )
        self.assertEqual(columns, preview_columns)
        self.assertEqual((width, header_width), (3, 3))
        rows = list(M02001.iter_upload_data_rows(
            stream, "export.xlsx", "excel", ",", "", "Y", None, width,
        ))
        self.assertEqual(rows, preview_rows)
        inspection = M02001.inspect_quick_edit_upload(stream, "export.xlsx", "excel", ",", "", "Y", "auto")
        self.assertEqual(inspection["columnCount"], 3)
        self.assertEqual(inspection["checkedDataRows"], 2)
        self.assertEqual(inspection["issues"], [{"code": "TOO_FEW_ROWS", "rows": 2, "minimum": 32}])
        self.assertFalse(stream.closed)
        self.assertEqual(stream.tell(), 0)

    def test_excel_genuine_single_cell_and_empty_sheet_are_preserved(self):
        from openpyxl import Workbook

        for value, expected in (("HEADER", [["HEADER"]]), (None, [])):
            with self.subTest(value=value):
                workbook = Workbook()
                if value is not None:
                    workbook.active["A1"] = value
                stream = io.BytesIO()
                workbook.save(stream)
                workbook.close()
                self.assertEqual(list(M02001.iter_excel_rows(stream, "single.xlsx")), expected)
                self.assertFalse(stream.closed)
                self.assertEqual(stream.tell(), 0)

    def test_schema_probe_reads_header_and_late_wide_row_is_rejected(self):
        stream = io.BytesIO(b"A,B\n1,2\n3,4,5\n")
        columns, width, header_width = M02001.inspect_upload_schema(
            stream,
            "sample.csv",
            "csv",
            ",",
            "",
            "Y",
            "utf-8",
        )

        self.assertEqual(columns, ["A", "B"])
        self.assertEqual((width, header_width), (2, 2))
        rows = M02001.iter_upload_data_rows(
            stream,
            "sample.csv",
            "csv",
            ",",
            "",
            "Y",
            "utf-8",
            width,
        )
        with self.assertRaises(HTTPException) as raised:
            list(rows)
        self.assertEqual(raised.exception.status_code, 400)

    def test_array_dml_uses_larger_batches_and_fewer_commits(self):
        connection = FakeUploadConnection()
        cursor = FakeUploadCursor()
        table_name = M02001.create_upload_staging_table_name()
        upload_columns = ["FILE_ROW_NO", *[f"COL{index:03d}" for index in range(1, 61)]]
        rows = ([str(row_index)] * 60 for row_index in range(5000))

        with patch.object(M02001, "UPLOAD_INSERT_BATCH_SIZE", 2000), patch.object(
            M02001,
            "UPLOAD_INSERT_BATCH_CELL_LIMIT",
            120000,
        ), patch.object(
            M02001,
            "UPLOAD_INSERT_BATCH_BYTE_LIMIT",
            16 * 1024 * 1024,
        ), patch.object(M02001, "can_use_upload_direct_path", return_value=False):
            result = M02001.load_upload_rows(connection, cursor, table_name, upload_columns, rows)

        self.assertEqual(result["rowCount"], 5000)
        self.assertEqual(result["batchCount"], 3)
        self.assertEqual(cursor.batch_sizes, [1967, 1967, 1066])
        self.assertEqual(result["commitCount"], 1)
        self.assertEqual(connection.commit_count, 1)
        self.assertGreaterEqual(result["parseAndBindSeconds"], 0)
        self.assertGreaterEqual(result["oracleLoadSeconds"], 0)
        self.assertGreaterEqual(result["commitSeconds"], 0)

    def test_direct_path_mode_loads_only_the_disposable_stage(self):
        connection = FakeDirectPathConnection()
        cursor = FakeUploadCursor()
        table_name = M02001.create_upload_staging_table_name()
        rows = ([str(row_index), str(row_index + 1)] for row_index in range(10))

        with patch.object(M02001, "can_use_upload_direct_path", return_value=True), patch.object(
            M02001,
            "get_current_schema_name",
            return_value="OWNER1",
        ):
            result = M02001.load_upload_rows(
                connection,
                cursor,
                table_name,
                ["FILE_ROW_NO", "COL001", "COL002"],
                rows,
            )

        self.assertEqual(result["loadMode"], "DIRECT_PATH")
        self.assertEqual(result["rowCount"], 10)
        self.assertEqual(len(connection.loads), 1)
        self.assertEqual(connection.loads[0][0:2], ("OWNER1", table_name))
        self.assertEqual(cursor.batch_sizes, [])
        self.assertGreaterEqual(result["parseAndBindSeconds"], 0)
        self.assertGreaterEqual(result["oracleLoadSeconds"], 0)

    def test_staged_finalization_returns_cached_result_on_retry(self):
        request = object()
        operation_request = M02001.build_staged_operation_request(
            "UPLOAD",
            "11",
            "PROJECT_A",
            table_name_rule="INITUP$_{PROJECT_CODE}_FT_{TIME}",
        )
        upload_id = "a" * 32
        with tempfile.TemporaryDirectory() as temp_directory, patch.object(
            M02001,
            "UPLOAD_STAGING_DIRECTORY",
            Path(temp_directory),
        ), patch.object(M02001, "get_request_user_id", return_value=7):
            data_path, _metadata_path = M02001.get_staging_paths(upload_id)
            data_path.touch()
            M02001.write_staged_upload_metadata(
                upload_id,
                {
                    "uploadId": upload_id,
                    "userId": "7",
                    "fileName": "sample.csv",
                    "expectedSize": 0,
                    "receivedSize": 0,
                    "createdAt": time.time(),
                },
            )
            metadata, finalized_data_path, cached, lock_path = M02001.begin_staged_finalization(
                request,
                upload_id,
                operation_request,
            )
            self.assertIsNone(cached)
            self.assertEqual(finalized_data_path, data_path)
            result = {"status": "success", "tableName": "INITUP$_PROJECT_A_FT_1234567890123"}
            M02001.finalize_staged_upload(upload_id, metadata, operation_request, result)
            M02001.release_staged_finalization_lock(lock_path)

            _metadata, no_data_path, cached, no_lock = M02001.begin_staged_finalization(
                request,
                upload_id,
                operation_request,
            )
            self.assertEqual(cached, result)
            self.assertIsNone(no_data_path)
            self.assertIsNone(no_lock)

    def test_upload_metadata_and_statistics_sql_include_safety_fields(self):
        tree_sql = SqlLoader.get_sql("M02001_UPLOAD_TABLE_TREE")
        merge_sql = SqlLoader.get_sql("M02001_UPLOAD_TABLE_META_MERGE")
        reserve_sql = SqlLoader.get_sql("M02001_UPLOAD_TABLE_META_RESERVE")
        stats_sql = SqlLoader.get_sql("M02001_UPLOAD_TABLE_STATS_GATHER")

        self.assertIn("M.PROJECT_ID = :projectId", tree_sql)
        self.assertIn("NVL(M.LOAD_STATUS, 'READY') = 'READY'", tree_sql)
        self.assertIn(":contentSha256 AS CONTENT_SHA256", merge_sql)
        self.assertIn("'LOADING'", reserve_sql)
        self.assertIn("FOR ALL COLUMNS SIZE 1", stats_sql)
        self.assertIn("cascade => FALSE", stats_sql)


if __name__ == "__main__":
    unittest.main()
