# 인에디타원 전환 기록 · 2026-10-26

제품명은 **인에디타원 / IN-EDITAONE**, 설명은 **INIT One-Stop Data Editing&Imputation Solution**입니다. 현재 프로젝트 폴더는 `D:\work\in-editaone`입니다.

## 적용 내용

- 로그인·메뉴·도움말·퀵 에디팅·보고서·XLSX 메타데이터·다운로드 이름·API 문서 제목을 새 브랜드로 변경합니다.
- 로고는 제공된 시안의 남색 워드마크와 체크 표시를 반영한 SVG 및 PNG입니다. 모든 compact·banner 변형에서 한글명 `인에디타원`을 함께 표시하고, 배너는 영문 워드마크 → 한글명 → 제품 설명 순으로 구성합니다. 원본 시안과 생성 코드는 `reference/branding/`에 보관합니다.
- 24쪽 제품 소개 PDF는 기존 본문·페이지 구성·회사 로고를 보존하고 제품명·제품 로고를 변경합니다. 이전 PDF·이미지 URL은 새 콘텐츠의 호환 별칭으로 유지합니다.
- 기존 DB 기본 표시명과 로고 경로는 `backend/branding.py`에서 응답 시에만 변환합니다. 고객이 지정한 이름·외부 URL은 유지합니다. 저장 데이터에 UPDATE를 실행하지 않습니다.
- 테이블명, SQL, 데이터, API URL 경로, 인증 정책, 환경변수 키, 브라우저 저장 키, 내부 DOM ID는 유지합니다.
- 스크립트는 위치 기준으로 루트를 계산합니다. 백업명과 Git 커밋 접두어는 새 이름을 쓰며, 실제 Render URL은 `-DeployUrl` 또는 `RENDER_EXTERNAL_URL`로 전달합니다.

## 폴더 이동 완료

현재 물리 경로는 `D:\work\in-editaone`이며 이전 프로젝트 폴더는 존재하지 않습니다. 관리형 개발 서버와 가상환경도 새 경로를 사용합니다. VS Code는 새 폴더를 열고, 이동 전에 활성화했던 터미널은 다시 엽니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\work\in-editaone\scripts\start-service.ps1 -Reload
powershell -NoProfile -ExecutionPolicy Bypass -File D:\work\in-editaone\scripts\stop-service.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File D:\work\in-editaone\scripts\restart-service.ps1 -Reload
```

`rename-project.ps1`과 `complete-project-rename.ps1`은 이전 이름의 폴더를 같은 상위 폴더의 `in-editaone`으로 바꾸는 이전 도구입니다. 현재 새 폴더에서 재실행하면 완료 메시지 후 종료하고 서버를 중지하거나 재시작하지 않습니다. 다른 PC에서는 폴더 이름을 강제하지 않고 서비스 스크립트가 자신의 위치로 프로젝트 루트를 계산합니다.

같은 PC에서 venv CLI 경로를 다시 복구해야 하면 프로젝트 루트에서 다음을 실행합니다. 설치 패키지는 추가·제거하지 않습니다.

```powershell
.\venv\Scripts\python.exe scripts/repair-venv-paths.py
.\venv\Scripts\pip.exe --version
.\venv\Scripts\pip3.exe --version
.\venv\Scripts\pip3.12.exe --version
.\venv\Scripts\uvicorn.exe --version
```

버전이 붙은 pip 이름은 Python 3.12 기준입니다. 다른 PC로 이동할 때는 venv를 복사해 재사용하지 않고 `reference/environment/README.md`대로 설치합니다.

폴더 변경 당시 VS Code·터미널·Codex 도구의 디렉터리 잠금은 별도 숨김 대기 작업으로 처리했습니다. 폴더 변경·런처 복구·서버 재시작은 완료됐으나 Windows PowerShell이 정상 테스트 진행 문자를 stderr 오류로 처리하면서 대기 작업에 실패 상태가 남았습니다. 이동 후 재점검에서 실제 테스트 종료 코드와 새 경로 실행 결과를 확인해 완료 상태를 갱신했습니다. 당시 작업 위치 기록은 `.runtime/pending-project-rename.json`에 보관합니다.

## GitHub와 Render

GitHub 저장소 이름 변경을 완료했습니다. 현재 저장소는 `https://github.com/initgroup/in-editaone`이며 로컬 `origin`도 새 Git 주소를 사용합니다. `git-publish-main.ps1`은 `RepositoryUrl`의 기본값을 `https://github.com/initgroup/in-editaone.git`으로 두고, 실행할 때 선택한 원격의 fetch·push 주소를 모두 맞춥니다. 원격이 없으면 추가합니다. 다음은 수동 연결 확인 명령입니다.

```powershell
git remote set-url origin https://github.com/initgroup/in-editaone.git
git ls-remote origin HEAD
```

Render의 기존 서비스를 그대로 사용하고, Settings에서 Git 저장소 연결이 새 URL을 가리키는지 확인합니다. 저장소명 변경만으로 운영 도메인까지 변경되었다고 가정하지 않습니다. 서비스 URL을 바꿀 경우 Dashboard가 실제로 부여한 URL을 사용합니다. 새 서비스 생성이나 DB 재생성은 필요하지 않습니다.

- Build Command: `bash scripts/render-build.sh`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Root Directory: 현재 루트 배포라면 빈 값 유지. 이전 프로젝트 폴더명을 하위 디렉터리로 적어둔 경우 수정.
- 운영 URL이 바뀐 경우에만 `INIT_ALLOWED_ORIGINS`를 실제 새 origin으로 갱신. 이 값은 쉼표로 구분하며 필요하면 전환 기간 동안 기존 origin도 유지.
- `INIT_SECRET_KEY`, DB 계정·비밀번호, `INIT_INTERNAL_API_KEY`, `INIT_INTERNAL_API_USER_ID`, `INIT_INTERNAL_API_CONNECTION_ID`는 제품명 변경으로 교체하지 않음. 암호화 키를 바꾸면 기존 비밀값을 해독하지 못할 수 있음.
- `INIT_COOKIE_SECURE=Y`, `INIT_COOKIE_SAMESITE=lax` 등 보안 설정 유지. 호스트를 바꾸면 기존 쿠키가 전달되지 않으므로 새 주소에서 다시 로그인.
- `RENDER_EXTERNAL_URL`은 Render가 제공하는 실제 서비스 URL입니다. 로컬 배포 스크립트에는 확인한 주소를 `-DeployUrl`로 전달할 수 있습니다.

[Render 환경변수 설정](https://render.com/docs/configure-environment-variables), [기본 제공 환경변수](https://render.com/docs/environment-variables), [배포 동작](https://render.com/docs/deploys)을 참고합니다. 환경변수 수정은 재배포에 반영해야 합니다.

## 사용자가 확인할 로컬 환경·DB 저장값

`.env`, 지갑 및 비밀 파일은 읽거나 변경하지 않았습니다. 아래 항목은 코드·스키마상 점검 대상이며 실제 DB에서 옛 값이 발견되었다는 의미가 아닙니다.

| 위치 | 확인 대상 | 필요한 조치 |
| --- | --- | --- |
| 로컬 `.env` | `DB_WALLET_PATH`, `DB_CLIENT_PATH` | 옛 프로젝트 절대경로가 있으면 새 경로 또는 프로젝트 기준 상대경로로 변경 |
| Render Environment | `INIT_ALLOWED_ORIGINS` | 실제 운영 도메인을 바꾼 경우에만 변경 |
| M91001 Target DB 연결, `INIT$_TB_DB_CONNECTION.WALLET_PATH` | 옛 폴더를 가리키는 로컬 지갑 절대경로 | 해당 연결의 경로만 새 폴더로 변경. 지갑 내용·DB DSN·계정은 유지 |
| M91002 GENERAL | `SYSTEM_DISPLAY_NAME`, `SYSTEM_LOGO_IMAGE` | 과거 기본값은 읽기 호환 처리하므로 필수 DB 변경 없음. 사용자 지정 옛 브랜드 문구는 필요 시 화면에서 직접 변경 |
| M90002 API 등록, `INIT$_TB_OML_RESOURCE.EXEC_API` / `SPEC_JSON` | 자기 서비스의 옛 절대 URL | 실제 도메인이 바뀌었을 때만 대상 항목을 화면에서 변경. `/api/...` 상대 경로는 유지 |
| 저장된 JOB·FLOW 파라미터와 외부 예약 호출 | 옛 자기 서비스 절대 URL / 파일 절대경로 | 필요한 개별 설정만 검토. 과거 실행 이력·결과와 업무 데이터는 일괄 치환하지 않음 |

실제 DB 접속·DDL·DML은 이번 브랜딩 검증에서 실행하지 않습니다. 전체 DB 문자열 치환은 하지 않습니다.

폴더명 변경 후 존재하지 않는 옛 프로젝트 절대경로는, 같은 상대경로가 새 프로젝트 안에 존재할 때 시스템 DB 및 Target DB 연결 경로 해석에서만 새 경로로 연결합니다. 기존 경로가 실제로 존재하거나 프로젝트 밖을 가리키면 변경하지 않습니다. `.env`나 DB의 원래 문자열은 보존됩니다.

## 검증 결과

- 백엔드 오프라인 회귀 449개 통과(브랜딩·경로 호환 검사 포함).
- 프런트 회귀 178개, 기본형·맞춤형 보고서 회귀 44개 통과.
- 한글/영문 로그인, 1440px/430px 레이아웃, 로고 로딩, 도움말 및 옛 URL 이동을 Chromium에서 확인.
- 실제 Chromium 한글 PDF 생성, 24쪽 소개서 렌더링 확인.
- Python compileall, 프런트 JSON, PowerShell 파싱, 다른 작업 폴더에서 루트 계산 확인.
- 별도 임시 venv를 실제로 옛 이름에서 새 이름으로 이동한 뒤 런처 재생성 및 `pip.exe --version` 실행 성공. 현재 서비스의 새 시작·종료·재시작 스크립트도 실제 8000 포트에서 실행 확인.
- Working 백업 실제 실행 성공. `.env`·지갑·비밀 디렉터리 제외 및 `.env.example` 포함 확인. 검증 백업은 `%TEMP%/in-editaone-migration-backups/`에 생성했습니다.
- FastAPI health, 인증 없는 보호 API 거부, 참조/DB 파일 정적 비공개 확인.
- `database/` 파일은 Git diff 기준 변경 없음. DB 데이터·스키마·환경 비밀값 변경 없음.
- 로컬 origin: `https://github.com/initgroup/in-editaone.git`. 사용자 확인에 따라 GitHub 저장소 이름 변경도 완료됐습니다. 배포 스크립트의 기본 저장소 주소와 실행 시 fetch·push 연결 설정을 새 주소로 반영했습니다. 실제 GitHub main 브랜치 읽기 접근, 로컬 fetch·push 주소, PowerShell 구문 및 기존/미등록 원격의 모의 실행을 확인했습니다. 이번 수정 작업에서는 커밋·push·Render 배포를 실행하지 않았습니다.
- 실제 프로젝트 폴더를 `D:\work\in-editaone`으로 변경했습니다. 새 경로의 venv 런처 복구와 개발 서버 시작을 확인했습니다. 이전 폴더는 존재하지 않습니다.
- 자료 생성 스크립트 4개의 옛 절대경로를 파일 위치 기준으로 변경했습니다. JavaScript·PowerShell 구문 검사, 경로 호환 오프라인 테스트 2개, 다른 작업 폴더에서 서비스·이름 변경 스크립트의 경로 계산을 확인했습니다.
- 실제 Oracle 업무 실행과 Render 운영 배포는 검증하지 않았습니다.

## 폴더 변경 후 재점검 · 2026-10-26

- 실행 소스·문서·설정·자료 생성 코드 542개를 검색했습니다. Markdown 11개와 PowerShell 11개를 모두 포함하며 UTF-8·문서 제어문자·JSON 문법도 확인했습니다. SQL과 SVG의 이전 프로젝트명 참조도 별도로 검색했습니다.
- README·개발 환경·환경 재현 안내와 작업 메모의 현재 경로를 정리했습니다. 자료 생성 메타데이터는 프로젝트 절대경로 대신 파일명으로 저장하며, 기존 Windows 경로도 읽을 수 있습니다.
- `complete-project-rename.ps1`은 완료 후 재실행하면 즉시 종료합니다. 실제 실행 전후 서비스 PID·생성 시각이 같아 서버를 중단하지 않는 것을 확인했습니다.
- `codex-venv.ps1`은 다른 작업 폴더에서 호출해도 프로젝트 루트에서 Python을 실행하고, stderr의 정상 출력과 프로세스 실패 종료 코드를 구분합니다. 성공 코드 0과 실패 코드 7 전달을 확인했습니다.
- 버전이 붙은 `pip3.12.exe`에 남아 있던 이전 경로를 복구했습니다. 복구 스크립트는 실행 중인 Python 버전의 pip 런처도 재생성합니다. venv 실행·활성화 파일 21개에 이전 프로젝트 경로가 없으며 pip·pip3·pip3.12·uvicorn 실행을 확인했습니다.
- PowerShell 11개, JavaScript 10개, Bash 1개의 구문 검사와 Python compileall을 통과했습니다. VS Code 작업 7개의 스크립트 경로와 인터프리터 경로를 확인했습니다.
- 백엔드 오프라인 회귀 449개, 퀵 에디팅 프런트 회귀 178개, 기본형·맞춤형 보고서 오프라인 회귀 44개를 새 폴더에서 다시 실행해 모두 통과했습니다. 관리형 서비스의 health 응답은 HTTP 200입니다.
- 배포용 `requirements.txt`, `package.json`, `package-lock.json`과 `reference/environment/`의 복제본이 바이트 단위로 일치합니다. 의존성 설치·추가·삭제는 하지 않았습니다.
- 남은 이전 프로젝트명은 경로 호환 모듈·회귀 테스트·이전 도구와 GitHub 전환 기록에서만 사용합니다. 임시 재브랜딩 변환 코드의 이전 문자열도 변환 입력으로 유지합니다. 설치된 외부 라이브러리, 임시 검증용 가상환경과 과거 렌더링 산출물은 실행 소스 점검 대상에서 제외합니다.
- `.env`·지갑·비밀 파일은 읽거나 변경하지 않았습니다. 실제 Oracle 업무 실행, Git commit/push 및 Render 배포는 이번 재점검에서 수행하지 않았습니다. Git 배포·백업 스크립트는 구문과 경로 계산을 확인했습니다.
