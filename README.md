# 인에디타원 · IN-EDITAONE

**INIT One-Stop Data Editing&Imputation Solution**

제품 로고는 영문 워드마크와 한글명 **인에디타원**을 함께 표시합니다. 배너에는 제품 설명을 추가하며, 로그인·사이드바·도움말에서도 같은 이름을 사용합니다.

프로젝트 기본 경로는 `D:\work\in-editaone`, Git 주소는 `https://github.com/initgroup/in-editaone.git`입니다. GitHub 저장소 이름 변경도 완료했습니다. [전환 안내](reference/BRAND_MIGRATION.md)에서 연결·배포 절차를 확인합니다. 로고·도움말·보고서 표시명 변경은 기존 테이블명, SQL, 사용자 데이터, API 경로, 인증·설정 키를 변경하지 않습니다.

실행 소스는 `frontend/`, `backend/`, `database/`, `quick-edit/`, `simple-edit/`에, 환경 재현 목록·브랜드 제작 원본은 [reference/](reference/README.md)에 보관합니다.

브라우저 탭과 바로가기에는 기존 로고의 체크 표시 ‘O’를 사용합니다. SVG·PNG는 `frontend/assets/ineditaone-icon*`, Windows 다중 해상도 아이콘은 `frontend/favicon.ico`이며 `node reference/branding/build-icons.mjs`로 재생성합니다(기존 Playwright·Chromium 사용). 바탕화면에 기본 브라우저로 로컬 서비스를 여는 **인에디타원** 바로가기를 만들려면 아래 명령을 실행합니다. 서비스는 먼저 시작되어 있어야 합니다. 운영 주소는 `-Url 'https://실제서비스주소/'`로 지정합니다. 프로젝트 이동 후에는 아이콘 경로 갱신을 위해 다시 실행합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\create-desktop-shortcut.ps1
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-service.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop-service.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\restart-service.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\backup-source.ps1 -Mode Working
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\git-publish-main.ps1
```

스크립트는 자신의 위치로 프로젝트 루트를 계산합니다. 다른 작업 폴더에서도 스크립트의 절대경로로 호출할 수 있습니다. 관리형 서비스 종료는 시작 스크립트가 기록하고 실행 파일·명령줄·생성 시각을 확인한 프로세스 트리만 종료합니다. 별도 터미널에서 실행한 reload 개발 서버는 해당 터미널에서 종료합니다. 백업의 `Git` 모드는 현재 커밋, `Working` 모드는 미커밋 수정까지 복사합니다. `git-publish-main.ps1`은 기본적으로 `origin`의 fetch·push 주소를 `https://github.com/initgroup/in-editaone.git`으로 설정하고 main에 반영합니다. 운영 URL 출력이 필요하면 `-DeployUrl`에 실제 주소를 전달합니다. Render 연결 상태도 확인합니다.

로컬 폴더명 변경을 완료했습니다. 다른 작업 폴더에서 서비스 명령을 실행할 때는 현재 프로젝트 경로를 사용합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\work\in-editaone\scripts\start-service.ps1 -Reload
powershell -NoProfile -ExecutionPolicy Bypass -File D:\work\in-editaone\scripts\stop-service.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File D:\work\in-editaone\scripts\restart-service.ps1 -Reload
```

Oracle 기반 데이터 편집/규칙 발굴 업무를 위한 FastAPI + 정적 프론트엔드 프로젝트입니다. 백엔드는 Oracle DB와 SQL 파일을 통해 업무 API를 제공하고, 프론트엔드는 `frontend/index.html`에서 페이지 HTML/JS를 동적으로 로드합니다.

## 기술 스택

- Backend: Python, FastAPI, Uvicorn, python-oracledb
- Frontend: Vanilla JavaScript, HTML, CSS, Tailwind CSS, Font Awesome, Grid.js
- Database: Oracle, SQL 파일 기반 쿼리 로딩

## 규칙 디스커버리 · 모바일 데모

메인 상단 버튼·첫 업무 메뉴의 **규칙 디스커버리(M00002)**에서 파일 선택 → 자동 사전 검사 → 규칙 찾기 → 결과로 진행합니다. 메인 대형 데모 배너는 제거했습니다. 기존 퀵 에디팅(M00001)은 유지합니다. `/simple-edit/` 직접 접속도 가능하며 분석에는 기존 서버 로그인이 필요합니다. Target DB 연결·프로젝트·테이블·JOB·FLOW 생성 없이 기존 Python 규칙 발굴 엔진을 호출합니다.

상단은 ƒ·⚡ 아이콘만 표시합니다. 한국어 툴팁은 각각 **핵심 규칙 요약 보기**, **규칙 분석·데이터 편집**이며, 두 화면은 공통 혼합형 엔진과 위반 판정 정책을 사용합니다. 규칙 디스커버리는 핵심을 요약하고 퀵 에디팅은 상세 분석·편집을 제공합니다. 요약 화면을 위한 별도 분석 알고리즘을 만들지 않습니다.

퀵 에디팅의 조건규칙·수식규칙은 모두 발굴방법 **혼합형 패턴**을 기본 선택합니다. 처음 결과를 열거나 규칙 유형을 전환하면 혼합형 결과를 먼저 조회하며, 전체·OML·Symbolic 결과는 발굴방법에서 선택합니다. 혼합형 결과가 없는 과거 이력은 해당 선택에서 0건으로 표시하고 다른 방법으로 조회할 수 있습니다. 규칙 디스커버리는 두 유형 모두 혼합형 패턴 엔진을 사용하며 분석 정보에서 확인할 수 있습니다.

새 퀵 작업은 **혼합형 단독 4단계**(`MIXED_XAI`)로 실행합니다. 기초통계 → 관계 → 조건·수식 규칙 발굴 → 위반 탐지에서 기존 OML/Symbolic 분석을 함께 실행하지 않습니다. 과거 `UNIFIED` 이력은 조회 시 보존하며, 퀵에서 다시 실행하면 같은 프로젝트·시나리오·원본으로 혼합형 FLOW의 새 실행을 준비합니다. 새 혼합형 JOB은 같은 대상의 통합 JOB에 저장된 혼합형 옵션을 이어받고, 이미 저장된 혼합형 JOB이 있으면 해당 설정을 재사용합니다. 진행 중인 과거 실행을 자동 중단하지 않습니다. 디스커버리는 기존부터 혼합형 한 경로입니다.

퀵 에디팅도 조건·수식 모두 **위반이 확인된 규칙만** 조회합니다. 서버에서 페이지를 나누기 전에 0건·탐지 미기록 규칙을 제외하며 유형별 건수와 필터도 같은 기준을 사용합니다. 탐지 미기록을 0건으로 간주하지 않고 조회 실패는 오류로 유지합니다.

**영업 데모:** 기본 메뉴에는 노출하지 않습니다. 메인 로그인 후 상단 **ƒ 아이콘(핵심 규칙 찾기)**을 누르면 독립 팝업이 열립니다. 같은 아이콘을 다시 누르면 기존 창과 결과를 유지하고 앞으로 가져옵니다. 모바일에서는 브라우저 정책에 따라 새 탭으로 열릴 수 있고, 팝업 차단 시 기존 작업 화면으로 연결합니다. 우측 상단 전체 화면 버튼과 파일 없이 실제 분석을 수행하는 **예제로 바로 체험**을 제공합니다.

**과거 실행:** 핵심 규칙 찾기 상단의 **과거 실행**에서 현재 Target DB의 퀵 에디팅 이력을 20건씩 조회합니다. 실행을 선택하면 저장된 혼합형 조건·수식 중 위반이 있는 규칙을 같은 핵심 요약 화면에 표시합니다(처음 3개, 유형별 최대 5개). 파일 업로드·재분석 없이 조회하며, 자세히 보기에서 저장된 위반 예시를 최대 100개까지 그래프·표로 확인합니다. 과거 실행에는 파일 데모의 1만 행 무작위 표본 제한을 새로 적용하지 않습니다. 저장되지 않은 원본 입력값·정상 행을 만들어 표시하지 않으며, Target DB가 연결되지 않았다면 메인에서 먼저 연결해야 합니다.

팝업은 같은 출처의 HttpOnly 세션 쿠키를 공유하며 로그인 정보나 토큰을 URL·JS 저장소로 복사하지 않습니다. 화면이 보이거나 분석 중일 때 로그인 필수 `/api/M00002/session`을 최대 90초 간격으로 확인해 서버 세션과 메인의 만료 표시를 갱신합니다. 숨겨진 유휴 창은 갱신하지 않으며 로그아웃·만료·서버 계정 변경을 확인하면 파일·결과와 진행 중 요청을 정리합니다. 서버 인증 정책은 유지합니다.

- CSV/TSV/XLSX/XLSM, 20MB 이하, 원본 데이터 32~200,000행·최소 2컬럼. 최대 100컬럼을 분석하고, 초과한 파일도 차단하지 않고 **원본 순서의 앞 100컬럼**만 사용합니다. 사전 검사와 결과 화면에 원본·분석·제외 컬럼 수를 안내합니다. 수식 데모에는 200행 이상 권장. 분석 대상의 첫 행은 빈 칸·중복 없는 한 줄 컬럼명, Excel은 활성 시트 사용. 파일 선택 시 전체 행의 너비와 분석 대상 셀 형식을 검사합니다.
- 최대 10,000행을 **파일 전체에서 균등 무작위 추출**합니다. 매 실행마다 새 난수를 사용하며 10,000행 이하에서는 전체 행을 사용하고 학습·검증 구간을 다시 나눕니다. 결과가 같을 수도 있고 달라질 수도 있습니다.
- 검증을 통과하고 **위반이 확인된 수식규칙·조건규칙**만 핵심 3개를 간결한 목록으로 먼저 보여주고, 더 보기에서 유형별 최대 5개까지 확인합니다. 상위 목록을 고르기 전에 전체 분석 표본에서 위반을 계산하며 0건 규칙으로 빈자리를 채우지 않습니다. 같은 컬럼 관계의 역방향 수식은 뒤로 배치해 다른 관계를 먼저 보여줍니다. 빠른 탐색을 위해 조건 대상 24개·수식 대상 12개로 제한합니다. 결과가 없으면 0건 안내를 표시합니다.
- 로딩은 상태·경과 시간을 하나의 패널에 표시하고 실제 진행률이 없는 작업에 임의 퍼센트를 붙이지 않습니다. 결과는 단일 목록, 상세는 규칙·탐지 집계·그래프/데이터 영역으로 구분하며 모바일과 팝업에 같은 디자인 기준을 적용합니다.
- 요약은 긴 수식 최대 2줄·적용 조건 1줄로 표시하고 위반 건수와 상세 버튼을 정렬합니다. 전체 식·조건은 툴팁과 상세에서 확인합니다. 각 규칙의 **자세히 보기**에서 그래프와 데이터를 탐색합니다. 수식은 계산값–실제값 산점도, 조건규칙은 일치·위반 후보 건수 그래프를 제공합니다. 그래프의 점·막대를 선택하면 입력값·해당 데이터로 연결되며, 필터·20행 단위 페이지·상세 표본 CSV 내려받기와 뒤로가기를 지원합니다.
- 채택한 규칙을 분석 표본 **전체(최대 1만 행)**에 적용해 위반 후보를 찾습니다. 규칙 선택 검증 지표는 별도로 보존하며 전체 원본의 오류율로 해석하지 않습니다. 화면 데이터는 일치·위반에서 나누어 고른 규칙별 최대 120개입니다. 표본 행 데이터는 128KiB, 셀 표시값은 160자로 제한합니다. 원본 순번은 헤더·빈 행을 제외한 원본 데이터 순서입니다. 학습한 AST·허용오차를 그대로 평가하며 재학습하지 않습니다. 설명·파일 조건·분석 범위는 펼침 도움말에 둡니다.
- 원본 수정·오류 정정·DB 결과 저장은 하지 않습니다. 업로드는 요청 처리 후 닫고 결과는 현재 화면 메모리에만 유지합니다. 전체 에디팅은 기존 퀵 에디팅을 사용합니다.
- 내려받는 예제는 소수의 배송유형·결제금액 입력 오류를 포함한 가상의 거래 2,400행입니다. [재생성 스크립트](reference/demo/generate_simple_edit_sample.py)가 [배포 예제 CSV](simple-edit/sample.csv)를 재현합니다. 추가 의존성·설치 DDL은 없습니다.

검증: `venv\Scripts\python.exe scripts/test_offline.py backend.tests.test_simple_editing backend.tests.test_simple_rule_details`, `node --test simple-edit/tests/mobile.test.js quick-edit/tests/embedded-workspace.test.js`. 오프라인 실제 엔진 검사와 모바일 브라우저 검사는 운영 Oracle 실행과 구분합니다.

## 통합 에디팅 4단계

2026-10-26 알고리즘 비교·보강: 숫자 문자열의 조건 구간 분석, 상관이 낮은 분모의 비율 탐색, 선택형 제곱근 수식과 최대 8항 합계 탐색을 기존 혼합형 엔진에 연결했습니다. 기존 수식 항 기본값 3·제곱근 비활성은 유지하며, 디스커버리 데모는 6항·제곱근을 사용합니다. 새 모델·라이브러리·추가 DDL은 없습니다. [비교 결과와 재현 방법](reference/benchmarks/README.md), [M90002·JOB 옵션 적용](INTEGRATED_EDITING_GUIDE.md#2026-10-26-수식-탐색-옵션)을 참고합니다.

기존 **컬럼 유형·기초통계 → 관계 분석 → 규칙 발굴 → 위반 탐지**와 전체 메뉴를 유지하면서, 각 단계의 Oracle 분석에 Python 혼합형 분석을 보강합니다. 새 통합 실행(`UNIFIED`)은 기존 분석과 혼합형 보강을 같은 FLOW에서 순차 수행하며, 저장된 `LEGACY`/`MIXED_XAI` 작업·설정·이력은 보존합니다.

숫자 문자열의 일부 오타, 전체 관계와 다른 소수 집단 수식, 범주형–연속형 관계, 제한된 해시 표본을 지원합니다. 양쪽 분석의 위반 건수는 겹칠 수 있으므로 합산치를 고유 오류 셀 수로 해석하지 않습니다. 새 Python 의존성·추가 DDL은 없지만 기존 OML 및 혼합형 저장 스키마 설치가 필요합니다.

Excel 입수 시 일부 외부 XLSX의 셀 범위가 `A1`로 잘못 기록돼 있어도 실제 셀을 읽습니다. 이전 버전에서 0행·1컬럼으로 입수된 파일은 서버 업데이트 후 파일을 다시 선택해 새 작업으로 입수해야 합니다. 기존 대상 테이블과 실행 이력은 자동 변경하지 않습니다. 혼합형 규칙 발굴에는 헤더를 제외한 데이터가 최소 32행 필요합니다.

퀵 에디팅의 새 파일은 임시 업로드 후 프로젝트·테이블·FLOW 생성 전에 사전 검사합니다. 다단 헤더로 보이는 구조, 데이터 32행 미만, 컬럼 2개 미만, 헤더보다 넓은 행, 셀당 UTF-8 4,000바이트 초과를 발견하면 파일 선택 영역에 수정 안내를 표시하고 중단합니다. 검사는 앞부분 데이터 최대 64행을 대상으로 하며 전체 파일 검증이나 모델 발굴 성공을 보장하지 않습니다. 실제 입수 시 전체 행 검증도 유지합니다.

사용·설정·실패 처리·Render 배포와 검증 범위는 [INTEGRATED_EDITING_GUIDE.md](INTEGRATED_EDITING_GUIDE.md), 혼합형 세부 기능은 [MIXED_XAI_GUIDE.md](MIXED_XAI_GUIDE.md)를 참고합니다. `database/ANALYSIS_SAMPLING.sql`은 서버가 로드하는 런타임 조회문이며 수동 설치 DDL이 아닙니다.

## 주요 구조

```text
.
├─ main.py                         # FastAPI 앱 진입점, 라우터 등록, 정적 파일 서빙
├─ backend/
│  ├─ database.py                  # 시스템 DB 연결 풀
│  ├─ target_database.py           # 로그인 후 선택한 Target DB 연결
│  ├─ database_helper.py           # SQL 파일 로더 및 execute_query
│  ├─ auth_context.py              # 서버 세션 쿠키 기반 인증/인가 컨텍스트
│  ├─ routers/                     # 화면/API별 라우터
│  └─ services/                    # 공통 업무 서비스
├─ database/                       # SQL ID별 쿼리 파일
├─ frontend/
│  ├─ index.html                   # SPA 셸
│  ├─ config/menu.config.js        # 메뉴와 페이지 파일 등록
│  ├─ config/flow-model-contracts.json # FLOW 모델별 단계·입출력·RUN 범위 계약
│  ├─ pages/                       # 화면 HTML
│  ├─ js/                          # 화면별 JS 및 공통 JS
│  └─ css/                         # 스타일/Tailwind 결과물
├─ requirements.txt
├─ package.json
└─ AGENTS.md                       # Codex 작업 가이드
```

## 프론트엔드 CSS 구조

이 프론트엔드는 SPA 구조이므로 CSS는 메뉴 전환 때마다 다시 로드하지 않고 `frontend/index.html`에서 한 번만 로드합니다.

- `frontend/css/styleMenu.css`: 여러 메뉴가 함께 쓰는 공통 페이지 스타일만 둡니다.
- `frontend/css/pages/{PAGE_CODE}.css`: 특정 메뉴 코드 하나에만 묶인 스타일을 둡니다. 예: `#container-M02001`, `.M04002-*`
- 여러 메뉴가 같은 클래스/선택자를 공유하면 메뉴별 CSS로 복사하지 않고 공통 CSS에 남깁니다.
- 메뉴별 CSS에는 다른 메뉴와 충돌하지 않도록 메뉴 코드가 포함된 고유 선택자를 사용합니다.
- 새 메뉴 CSS 파일을 추가하면 `frontend/index.html`의 `APP_PAGE_CSS_FILES`에 등록합니다.
- CSS 캐시를 갱신할 때는 `APP_CACHE_VERSION`을 올리고, 별도 override가 있는 파일은 `APP_ASSET_VERSION_OVERRIDES`도 함께 확인합니다.

## 실행 방법

Python 가상환경을 준비합니다.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

필요한 환경 변수는 `.env.example`을 복사해 `.env`에 설정합니다. `.env`, `secreats/`, `instantclient/`는 비밀 정보 또는 로컬 의존성이므로 Git에 올리지 않습니다.

```text
DB_MODE=local 또는 cloud
DB_USER_LOC=...
DB_PASSWORD_LOC=...
DB_HOST=127.0.0.1
DB_PORT=1521
DB_SERVICE=...

DB_USER_CLD=...
DB_PASSWORD_CLD=...
DB_DSN_CLD=...
DB_WALLET_PATH=secreats/Wallet_INITGROUPEDITING
DB_ORACLE_MODE=thin

DB_POOL_MIN=1
DB_POOL_MAX=5
DB_POOL_INCREMENT=1

TARGET_DB_POOL_MIN=0
TARGET_DB_POOL_MAX=3
TARGET_DB_POOL_INCREMENT=1
TARGET_DB_POOL_TIMEOUT_SECONDS=120
TARGET_DB_POOL_WAIT_TIMEOUT_MS=30000
APP_RULE_SUMMARY_TIMEOUT_MS=60000
TARGET_DB_POOL_MAX_LIFETIME_SECONDS=1800
TARGET_DB_POOL_REGISTRY_MAX=16
DATA_WORK_TRANSACTION_TIMEOUT_SECONDS=1800
DATA_WORK_TRANSACTION_SWEEP_SECONDS=60
APP_ML_MAX_CONCURRENT=1
APP_ML_WAIT_SECONDS=0
APP_ML_MAX_IN_MEMORY_ROWS=25000
APP_ML_MAX_INPUT_FEATURES=50
APP_ML_FETCH_BATCH_ROWS=1000
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1
APP_BATCH_WORKERS=1
APP_BATCH_QUEUE_CAPACITY=4
APP_BATCH_SUBMIT_WAIT_SECONDS=0
APP_BATCH_SHUTDOWN_WAIT_SECONDS=10
APP_AI_QUERY_MAX_ROWS=1000
APP_AI_QUERY_MAX_RESPONSE_BYTES=4194304
APP_AI_QUERY_MAX_CELL_BYTES=262144
APP_AI_QUERY_FETCH_BATCH_ROWS=25
APP_EXTERNAL_API_MAX_RESPONSE_BYTES=10485760
APP_GEMINI_MAX_REQUEST_BYTES=20971520
APP_GEMINI_MAX_QUERY_CHARS=20000
APP_GEMINI_MAX_ATTACHMENTS=8
APP_GEMINI_MAX_TEXT_CHARS=180000
APP_GEMINI_MAX_METADATA_CHARS=20000
APP_GEMINI_MAX_ATTACHMENT_BYTES=4194304
APP_GEMINI_MAX_TOTAL_BINARY_BYTES=12582912

# 운영 보안 설정
INIT_SECRET_KEY=충분히 긴 랜덤 문자열
INIT_ALLOWED_ORIGINS=https://your-render-service.onrender.com
INIT_COOKIE_SECURE=Y
INIT_COOKIE_SAMESITE=lax
INIT_SESSION_TTL_SECONDS=3600

# 내장 Python API를 외부에서 직접 호출해야 하는 경우에만 설정
INIT_INTERNAL_API_KEY=충분히 긴 랜덤 API 키
INIT_INTERNAL_API_USER_ID=내장 API 실행 전용 사용자 USER_ID
INIT_INTERNAL_API_CONNECTION_ID=기본 Target DB CONNECTION_ID
```

### 서버 리소스 제한과 M91002 설정

`TARGET_DB_POOL_WAIT_TIMEOUT_MS`, `APP_RULE_SUMMARY_TIMEOUT_MS`, `APP_ML_MAX_IN_MEMORY_ROWS`, `APP_ML_MAX_INPUT_FEATURES` 환경변수는 서버 프로세스의 안전 상한입니다. Render 무료 인스턴스의 Target DB 연결 지연을 고려해 풀 대기 기본값은 30초(`30000ms`), 규칙 요약 브라우저 요청 제한은 60초(`60000ms`)이며, ML 분석은 기본적으로 한 번에 최대 25,000행과 50개 피처를 메모리에 적재합니다.

M91002의 `SERVER_RESOURCE_LIMITS` 카테고리에서는 같은 키를 사용자 및 Target DB 연결별 요청값으로 관리합니다. 실제 적용값은 `min(M91002 요청값, 서버 환경변수)`이므로 M91002에서 서버 상한을 높일 수 없고, 더 보수적인 값으로 낮출 수만 있습니다. 설정은 로그인 시 한 번 서버의 bounded LRU 캐시에 적재되어 세션 동안 재사용되며, M91002에서 저장·삭제·기본값 생성을 수행한 경우에만 해당 사용자/연결 캐시가 무효화됩니다. 프로세스 재시작 또는 로그인 전환 뒤에는 다시 적재됩니다. 유료 인스턴스 등에서 상한 자체를 늘리려면 배포 환경변수를 먼저 조정한 뒤 M91002 값을 설정해야 합니다.

## 보안 기준

- 로그인 후 인증은 `HttpOnly` 세션 쿠키와 시스템 DB의 `INIT$_TB_AUTH_SESSION`으로 검증합니다. 브라우저의 `sessionStorage`, GET/POST 파라미터, `X-Login-*` 헤더를 권한 근거로 사용하지 않습니다.
- `/api/**`는 기본적으로 로그인 세션이 필요합니다. 로그인, 회원가입, 관리자 연락처, 최초 bootstrap 설치처럼 명시된 API만 공개 예외입니다.
- 관리자 메뉴 API(`M99001`, `M99002`, `M99003`, `M99004`)는 서버 세션의 ADMIN 역할로만 접근할 수 있어야 합니다. 프론트 메뉴 숨김만으로 관리자 권한을 처리하지 않습니다.
- DB 비밀번호, 지갑 비밀번호, 개인 API Key는 브라우저 응답에 내려보내지 않습니다. `INIT_SECRET_KEY`가 설정된 환경에서는 새 비밀값이 Fernet 암호문으로 저장되며, 기존 `b64:` 값은 읽기 호환만 유지합니다.
- `database/`, `.env`, `secreats/`, `instantclient/`, 지갑 ZIP, 백엔드 소스는 정적 파일로 노출되면 안 됩니다.
- 동적 SQL은 화면/업무별 허용 범위 안에서만 실행합니다. 일반 SELECT 경로는 읽기 전용으로 제한하고, PL/SQL 내부의 동적 DDL(`EXECUTE IMMEDIATE`, `DROP`, `TRUNCATE`, `ALTER`, `GRANT`, `REVOKE` 등)은 차단합니다.
- 내장 Python API를 HTTP로 직접 호출해야 할 때는 `X-INIT-API-Key` 또는 `Authorization: Bearer ...`를 사용하고, 서버 환경변수의 서비스 사용자/Target DB 연결로만 실행합니다.

개발 서버를 실행합니다.

```powershell
.\venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Render 배포와 기본형·맞춤형 보고서 PDF

`playwright.config.ts`의 `127.0.0.1:8000`은 UI 자동 테스트를 실행할 때만 사용하는 주소입니다. 기본형·맞춤형 보고서 PDF는 서버에서 HTML을 직접 Chromium에 전달하므로 Render 운영 URL을 이 파일에 설정하지 않습니다.

Playwright 자체는 [Apache License 2.0](https://github.com/microsoft/playwright/blob/main/LICENSE)으로 제공되므로 상용 서비스에서도 사용할 수 있습니다. 제품 배포 시에는 Playwright와 함께 사용하는 Chromium 및 의존 패키지의 LICENSE/NOTICE 고지 의무도 릴리스 절차에서 함께 확인합니다.

Render의 Python Web Service에서는 Dashboard의 **Build Command**를 다음과 같이 지정합니다.

```bash
bash scripts/render-build.sh
```

Git 자동 배포는 새 커밋으로 기존 Build Command를 실행할 뿐, Dashboard에 저장된 Build Command 자체를 저장소 내용으로 변경하지 않습니다. 기존 서비스가 `.\venv\Scripts\python.exe -m pip install -r requirements.txt`만 실행하고 있다면 위 명령으로 직접 변경한 뒤 **Clear build cache & deploy**를 한 번 수행해야 합니다.

이 스크립트는 Python 및 Node 의존성을 설치하고, Playwright Chromium을 프로젝트 내부에 설치합니다. Render Native Python 빌드는 root/su 권한을 제공하지 않으므로 `playwright install --with-deps`는 사용하지 않습니다. 마지막에는 실제 Chromium으로 작은 PDF를 생성하며, Build 로그에 `Playwright Chromium PDF smoke test passed.`가 없으면 해당 배포를 정상 PDF 배포로 판단하지 않습니다. **Start Command**는 기존 FastAPI 설정을 유지하되 외부 요청을 받을 수 있도록 `0.0.0.0`과 Render의 `PORT`를 사용해야 합니다.

PDF 한글은 운영체제 글꼴이나 외부 폰트 URL에 의존하지 않습니다. `npm ci`가 OFL-1.1 라이선스의 `@fontsource-variable/noto-sans-kr`를 설치하고, PDF 생성 시 필요한 Noto Sans KR 글꼴 데이터를 HTML에 직접 내장합니다. 한글이 포함된 PDF에서는 Chromium이 내장 글꼴을 확인하지 못하면 깨진 문서를 반환하지 않고 렌더링 오류로 중단합니다.

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

기존 Target DB에는 배포 전에 `database/INIT_TARGET_ALTER.sql`을 적용해 M06002 사용자별 맞춤형 보고서 템플릿과 프로젝트 사용 이력 테이블을 생성합니다. 신규 Target DB는 `database/INIT_TARGET_DDL.sql`에 포함되어 있으며, 애플리케이션도 최초 사용 시 선택된 Target DB에서 두 테이블을 확인해 누락된 설치를 보완합니다.

배포 후에는 M06001의 한국어 단건·통합 PDF와 M06002의 A4/A3 세로·가로 PDF를 각각 한 번 내려받아 Chromium 실행, 글꼴 표시, 페이지 방향과 메모리 사용량을 확인합니다. 운영 인스턴스의 메모리가 작다면 통합 PDF 동시 생성은 현재 설정처럼 한 번에 한 건으로 유지합니다.

브라우저에서 `http://127.0.0.1:8000`을 엽니다. API 문서는 `http://127.0.0.1:8000/docs`에서 확인할 수 있습니다.

Tailwind CSS를 수정할 때는 별도 터미널에서 빌드합니다.

```powershell
npx tailwindcss -i ./frontend/css/input.css -o ./frontend/css/output.css --watch
```

## 화면 추가 체크리스트

새 화면 코드가 `M12345`라고 가정합니다.

1. `backend/routers/M12345.py`를 만들고 `router = APIRouter()`를 정의합니다.
2. `main.py`에서 라우터를 import하고 `routers` 목록에 `(M12345.router, "M12345")`를 추가합니다.
3. `database/M12345.sql`에 `-- [M12345_...]` 형식으로 SQL ID를 작성합니다.
4. `frontend/pages/M12345.html`을 추가합니다.
5. `frontend/js/M12345.js`를 추가하고 `(function(){ ... window.M12345 = M12345; })();` 패턴을 사용합니다.
6. `frontend/config/menu.config.js`의 `MENU_CONFIG`, `PAGE_FILE_CONFIG.htmlPages`, `PAGE_FILE_CONFIG.scriptPages`에 화면 코드를 등록합니다.
7. API 호출은 `CommonUtils.request(`${API_BASE_URL}/M12345/...`)` 패턴을 사용합니다.

## SQL 작성 규칙

`backend.database_helper.SqlLoader`는 `database/*.sql` 파일을 읽고 `-- [SQL_ID]` 구분자를 기준으로 쿼리를 메모리에 로드합니다.

```sql
-- [M01001_PROJECT_LIST]
SELECT ...
  FROM ...
 WHERE (:keyword IS NULL OR ...)
```

- Python에서는 `execute_query(conn, "M01001_PROJECT_LIST", params)`처럼 SQL ID로 실행합니다.
- 바인드 변수는 `:camelCase` 또는 기존 파일의 관례에 맞춥니다.
- 테이블명/동적 SQL은 허용된 자리에서만 `dynamicTable`, `dynamicSql` 치환을 사용합니다.
- 사용자 입력으로 식별자나 SQL 조각을 만들 때는 라우터/서비스에서 검증 후 사용합니다.

## 요청 컨텍스트

프론트의 `CommonUtils.request`는 `credentials: "include"`로 `HttpOnly` 세션 쿠키를 함께 전송합니다. Target DB 선택값은 `X-Target-Connection-Id`로 전달할 수 있지만, 서버는 세션의 사용자 ID로 해당 연결 접근 권한을 다시 검증합니다.

업무 화면 라우터는 보통 `get_target_db_connection(request)`를 사용해 Target DB에 연결합니다. 사용자 ID, 로그인 ID, 이메일, 역할은 `backend.auth_context`에서 서버 세션을 통해 읽어야 하며 브라우저 헤더 값을 신뢰하면 안 됩니다. 시스템 설정/로그인/관리 기능은 필요에 따라 `get_db_connection()`으로 시스템 DB에 연결합니다.

## 4단계 통합 FLOW

퀵 에디팅은 홈 바로 아래 **퀵 에디팅(M00001)** 메뉴 또는 상단 바로가기로 메인 탭에서 엽니다. 다른 메뉴를 확인해도 실행 상태를 유지하며, 실제 데이터 규칙은 **조건규칙(IF–THEN)·수식규칙**으로 구분합니다. 발굴 방법은 각 규칙에 보존하며 과거 이상 후보 설명은 별도로 확인합니다. 목록은 서버에서 페이지 단위로 조회하고, 위반 행·통계는 필요할 때 불러옵니다. 적용과 진단 확인은 [INTEGRATED_EDITING_GUIDE.md](INTEGRATED_EDITING_GUIDE.md)를 참고하세요.

**혼합형 패턴 분석**은 퀵 에디팅의 기본 단독 4단계와 수동 통합 FLOW의 보강 기능에서 사용합니다. 실제 컬럼별 예측 트리와 수식으로 `IF 조건 THEN 실제 값·범위·수식`을 발굴하고, 별도 표본의 선택 검증을 통과한 규칙을 원본 전체에 적용합니다. 기존 규칙·위반 테이블과 최종 분석·에디팅 화면을 재사용합니다. 상세 FLOW에서는 기존 분석·혼합형·통합 구성을 선택할 수 있습니다. 과거 이력과 JOB은 보존하며 퀵의 통합 이력 재실행은 혼합형 FLOW에 새 실행을 만듭니다. Target DB 오브젝트는 분석 중 자동 생성하지 않습니다. 내장 API는 미등록 시 허용된 배포 프리셋으로 JOB을 준비하며, SQL 설치와 선택적인 M90002 등록은 [MIXED_XAI_GUIDE.md](MIXED_XAI_GUIDE.md)를 참고하세요. 반복 오류의 원인과 재발 방지 검증은 [QUICK_EDIT_RELIABILITY.md](QUICK_EDIT_RELIABILITY.md)에 기록합니다.

신규 기본 FLOW 템플릿은 다음 4개 내장 통합 API를 우선 선택합니다. 각 API는 기존 Oracle 분석과 Python 혼합형 보강을 순서대로 수행합니다. 개별 프로파일링·상관·군집·LASSO·Apriori·Symbolic 모델과 저장된 기존 JOB도 계속 사용할 수 있습니다.

1. `UNIFIED_EDITING_PROFILE`: 기존 컬럼 유형 판정과 표본 기초통계
2. `UNIFIED_EDITING_RELATION`: 기존 관계 행렬·네트워크와 혼합형 관계·품질 진단
3. `UNIFIED_EDITING_DISCOVER`: 기존 범주형·연속형 규칙과 혼합형 값·범위·수식 발굴
4. `UNIFIED_EDITING_DETECT`: 같은 실행의 기존·혼합형 규칙 위반 탐지

자동 생성된 JOB은 M03001~M03004의 작업 목록에서 열어 저장된 모델과 파라미터를 확인합니다. 미등록 내장 API로 준비한 JOB은 M90002 등록 ID가 없어도 저장된 계약으로 표시·저장·실행할 수 있습니다. M90002의 기본 Python API 생성은 미등록 항목만 추가하며 기존 설정이나 비활성 상태를 덮어쓰지 않습니다. 중앙 등록을 수정해도 과거 JOB의 설정은 자동 갱신되지 않습니다.

`flow-model-contracts.json`은 각 모델의 입력·출력 artifact, 필수 여부, `SAME_RUN`/`LATEST_MASTER` 범위를 정의합니다. FLOW 저장·실행 시 서버가 단계 건너뛰기와 동일 RUN 결과 누락을 검증하며, 통합 노드의 복수 결과는 `INIT$_TB_FLOW_WORK_NODE_RUN.RUN_OUTPUT_JSON`에 기록됩니다. 기존 Target DB에는 `INIT_TARGET_ALTER.sql`을 적용해야 합니다.

## 주의사항

- 현재 일부 기존 파일의 한글 주석/문자열이 깨져 보일 수 있습니다. 기존 인코딩을 일괄 변환하지 말고, 수정 범위 안에서만 UTF-8로 정리합니다.
- `.env`, 지갑 파일, Oracle Instant Client, DB 접속 정보는 커밋하지 않습니다.
- `.\venv\Scripts\python.exe scripts/test_offline.py`로 환경 파일과 Oracle·네트워크 연결을 차단한 백엔드 회귀 검사를, `node --test quick-edit/tests/*.test.js`로 프런트 회귀 검사를 실행합니다. 앱 기동 후 `/api/health`도 확인하며 오프라인 검사를 실제 Oracle 실행 검증과 구분합니다.

CPU 규칙 보완: 기존 혼합형 외부모델의 희소 인코딩을 재사용해 최대 128개의 단일 조건 지시자를 보완합니다. 기존 규칙·수식·모델/JOB 옵션과 위반 탐지 범위를 보존하며 새 모델이나 패키지를 설치하지 않습니다. [적용 판단·CPU/메모리 측정](reference/benchmarks/cpu-rule-mining-20261026/README.md). 검사는 변경한 기능과 직접 연결된 범위만 선택하며, 전체 검사를 매번 자동 실행하지 않습니다.
