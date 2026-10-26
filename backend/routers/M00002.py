"""Authenticated, transient file discovery for the mobile Rule Discovery demo."""
import logging

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile, Query

from backend.auth_context import get_request_user_id, get_session_ttl_seconds, get_request_role_code
from backend.services.simple_editing import analyze_file, inspect_file

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/session")
def session(request: Request, response: Response):
    """The shared auth middleware verifies and refreshes the browser session."""
    user_id = get_request_user_id(request)
    response.headers["Cache-Control"] = "no-store"
    return {"status": "success", "user": {"userId": user_id}, "sessionTtlSeconds": get_session_ttl_seconds(),
            "targetConnectionId": (getattr(request.state, "auth_user", None) or {}).get("targetConnectionId")}


@router.post("/analyze")
def analyze(request: Request, file: UploadFile = File(...)):
    return _process_file(request, file, analyze_file)


@router.post("/preflight")
def preflight(request: Request, file: UploadFile = File(...)):
    return _process_file(request, file, inspect_file)


def _process_file(request, file, operation):
    try:
        get_request_user_id(request)
        return operation(file.file, file.filename or "")
    except HTTPException:
        raise
    except (ValueError, UnicodeError) as error:
        raise HTTPException(400, {"code": "FILE_DATA", "message": "파일 내용 또는 데이터 형식을 확인해 주세요."}) from error
    except Exception as error:
        logger.exception("Rule Discovery failed")
        raise HTTPException(500, "규칙 분석을 완료하지 못했습니다. 잠시 후 다시 실행해 주세요.") from error
    finally:
        file.file.close()


@router.get("/history")
def history(request: Request, response: Response, page: int = Query(1, ge=1, le=1000000), pageSize: int = Query(20, ge=1, le=20)):
    response.headers["Cache-Control"] = "no-store"
    from backend.services.flow_work_service import list_quick_edit_history
    return _read_history(request, lambda conn, user, admin: list_quick_edit_history(conn, "M04001", user, admin, page, pageSize))


@router.get("/history/{run_id}")
def history_result(request: Request, response: Response, run_id: int, ruleKey: str = Query("", max_length=4096)):
    response.headers["Cache-Control"] = "no-store"
    from backend.services.simple_edit_history import read_history_result
    if run_id <= 0:
        raise HTTPException(400, "Invalid flow run ID.")
    return _read_history(request, lambda conn, user, admin: read_history_result(conn, run_id, user, admin, ruleKey))


def _read_history(request, operation):
    from backend.target_database import get_target_db_connection
    conn = None
    try:
        user = get_request_user_id(request)
        admin = get_request_role_code(request) == "ADMIN" and not getattr(request.state, "internal_api_authorized", False)
        conn = get_target_db_connection(request)
        return operation(conn, user, admin)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Key-rule history query failed")
        raise HTTPException(500, "과거 실행 결과를 불러오지 못했습니다. 다시 시도해 주세요.") from exc
    finally:
        if conn:
            conn.close()
