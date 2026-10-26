import json
import unittest
from unittest.mock import patch

from fastapi import HTTPException, Response
from starlette.requests import Request
from backend.services import simple_edit_history as service
from backend.routers import M00002
from backend.tests import test_editing_result_paging as paging


class StoredKeyRuleHistoryTests(unittest.TestCase):
    def setUp(self):
        fixture=paging.EditingResultPagingTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture=fixture
        run={"FLOW_RUN_ID":41,"STATUS":"SUCCESS","RUN_TYPE":"QUICK_EDIT","OWNER_NAME":"APP_OWNER","TABLE_NAME":"SOURCE_DATA",
             "PROJECT_ID":1,"PROJECT_NAME":"Project","SCENARIO_NAME":"Scenario"}
        self.history=patch.object(service.flows,"list_quick_edit_history",return_value={"status":"success","data":[run]})
        self.lookup=self.history.start(); self.addCleanup(self.history.stop)
        nodes=patch.object(service.flows,"list_node_run_history",return_value={"data":[]}); nodes.start();self.addCleanup(nodes.stop)

    def rule(self, identifier="F", violations=4):
        ast={"operator":"WITHIN_TOLERANCE","column":"Y","numericText":True,"absoluteTolerance":.01,"relativeTolerance":0,
             "expression":{"operator":"ADD","left":{"column":"X","numericText":True},"right":{"column":"Z","numericText":True}}}
        self.fixture.assoc(identifier,kind="FORMULA",VIOLATION_COUNT=violations,CONDITION_TOTAL_COUNT=100,SUPPORT_COUNT=100-violations if violations is not None else 100,RESULT_JSON=json.dumps(ast))

    def test_actual_catalog_filters_zero_unknown_before_top_five_and_is_read_only(self):
        for i in range(12):self.rule(f"ZERO{i}",0)
        self.rule("UNKNOWN",None)
        for i in range(7):self.rule(f"BAD{i}",i+1)
        self.fixture.assoc("CONDITION",VIOLATION_COUNT=2,CONDITION_TOTAL_COUNT=100,SUPPORT_COUNT=98,RESULT_JSON=json.dumps({"operator":"=","column":"Y","value":"1"}))
        data=service.read_history_result(self.fixture.conn,41,7)["data"]
        self.assertEqual(data["detectionScope"],"STORED_TARGET")
        self.assertEqual(data["counts"],{"FORMULA":7,"CONDITION":1})
        self.assertEqual([rule["detail"]["stats"]["different"] for rule in data["rules"]["FORMULA"]],[7,6,5,4,3])
        self.assertTrue(all(not rule["detail"]["loaded"] for rule in data["rules"]["FORMULA"]))
        self.assertEqual(0,self.fixture.conn.violation_rows)
        self.lookup.assert_called_with(self.fixture.conn,"M04001",7,False,1,1,flow_run_id=41)
        self.assertTrue(all(not sql.lstrip().upper().startswith(("INSERT","UPDATE","DELETE","MERGE")) for sql in self.fixture.conn.queries))

    def test_lazy_preview_preserves_saved_numeric_policy_and_data_identifiers(self):
        self.rule()
        catalog=service.read_history_result(self.fixture.conn,41,7)["data"]
        selected=catalog["rules"]["FORMULA"][0]
        for i,value in enumerate(("1013","invalid","1,013")):
            self.fixture.insert("INIT$_TB_RULEVIOL_ASSOC",VIOLATION_ID=i+1,RUN_SOURCE_TYPE="FLOW_WORK",RUN_ID=41,
                RULE_OWNER="APP_OWNER",TARGET_OWNER="APP_OWNER",TARGET_TABLE="SOURCE_DATA",MODEL_NAME="MIXED",RULE_ID="F",
                CASE_ID=f"CASE-{i+1}",ACTUAL_VALUE=value,EXPECTED_VALUE="1010")
        data=service.read_history_result(self.fixture.conn,41,7,rule_key=selected["storedRuleKey"])["data"]
        self.assertEqual(data["detail"]["cohort"],"STORED_DETECTION")
        self.assertEqual(data["detail"]["stats"],{"different":4,"applied":100,"matched":96})
        records={row["sourceRow"]:row for row in data["detail"]["rows"]}
        self.assertEqual(records["CASE-1"]["actual"],1013)
        self.assertEqual(records["CASE-1"]["residual"],3)
        self.assertEqual(records["CASE-2"]["status"],"UNSCORABLE")
        self.assertEqual(records["CASE-3"]["status"],"UNSCORABLE")
        self.assertEqual(data["detail"]["savedRows"],3)
        self.assertEqual(len(data["detail"]["inputs"]),0)

    def test_missing_or_unauthorized_quick_run_is_rejected_before_catalog(self):
        self.lookup.return_value={"status":"success","data":[]}
        with patch.object(service,"read_results") as catalog, self.assertRaises(HTTPException) as caught:
            service.read_history_result(self.fixture.conn,999,7)
        self.assertEqual(caught.exception.status_code,404);catalog.assert_not_called()

    def test_unrecorded_detection_is_not_a_clean_run_and_errors_stay_errors(self):
        self.rule("UNKNOWN",None)
        data=service.read_history_result(self.fixture.conn,41,7)["data"]
        self.assertEqual(data["rules"],{"FORMULA":[],"CONDITION":[]})
        self.assertEqual(data["discoveredCounts"]["FORMULA"],1)
        with patch.object(service,"read_results",side_effect=HTTPException(503,"Unavailable")),self.assertRaises(HTTPException):
            service.read_history_result(self.fixture.conn,41,7)

    def test_route_uses_verified_identity_role_and_closes_the_connection(self):
        request=Request({"type":"http","headers":[(b"x-login-user-id",b"999"),(b"x-login-role",b"ADMIN")]})
        class Connection:
            closed=False
            def close(self):self.closed=True
        conn=Connection()
        with patch.object(M00002,"get_request_user_id",return_value=7),patch.object(M00002,"get_request_role_code",return_value="USER"),patch("backend.target_database.get_target_db_connection",return_value=conn),patch.object(service.flows,"list_quick_edit_history",return_value={"data":[]}) as query:
            M00002.history(request,Response(),1,20)
        query.assert_called_once_with(conn,"M04001",7,False,1,20)
        self.assertTrue(conn.closed)
        with patch.object(M00002,"get_request_user_id",side_effect=HTTPException(401,"Login required")),patch("backend.target_database.get_target_db_connection") as connect,self.assertRaises(HTTPException):
            M00002.history(request,Response(),1,20)
        connect.assert_not_called()


    def test_rule_key_cannot_escape_the_authorized_run_or_target(self):
        self.rule()
        with self.assertRaises(HTTPException) as caught:
            service.read_history_result(self.fixture.conn,41,7,rule_key="not-a-rule-key")
        self.assertEqual(caught.exception.status_code,400)

    def test_target_header_is_compared_with_server_session_before_connection(self):
        from backend.target_database import get_target_connection_id
        request=Request({"type":"http","headers":[(b"x-target-connection-id",b"999")]})
        request.state.auth_user={"userId":7,"targetConnectionId":21,"roleCode":"USER"}
        with patch.object(M00002,"get_request_user_id",return_value=7),patch.object(M00002,"get_request_role_code",return_value="USER"),patch("backend.target_database.get_target_db_connection",side_effect=get_target_connection_id),self.assertRaises(HTTPException) as caught:
            M00002.history(request,Response(),1,20)
        self.assertEqual(caught.exception.status_code,409)
