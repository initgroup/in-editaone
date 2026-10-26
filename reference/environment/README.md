# IN-EDITAONE 설치 환경

이 디렉터리의 `requirements.txt`, `package.json`, `package-lock.json`은 루트 배포 파일과 같은 버전으로 유지합니다. `python-installed.txt`는 전환 시점 로컬 venv의 실제 설치 버전 기록입니다. 다른 운영체제에서는 Oracle·Windows 전용 패키지의 호환성을 확인합니다.

새 PC에서는 프로젝트 루트에서 다음을 실행합니다.

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
npx playwright install chromium
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-service.ps1
```

PDF 렌더러는 Node Playwright를 사용하므로 Chromium 설치는 `npx playwright install chromium`도 가능합니다. 로컬 `.env`는 `.env.example`을 참고해 사용자가 구성합니다. 실제 비밀번호·지갑·API 키를 이 디렉터리에 복사하지 않습니다. Oracle 휠은 `installers/`에 보관하며 바이너리는 Git 제외 대상입니다.

같은 PC에서 폴더명만 바꾼 경우에는 다음 명령이 설치 패키지를 바꾸지 않고 CLI 런처와 활성화 스크립트를 새 경로로 재생성합니다.

```powershell
.\venv\Scripts\python.exe scripts/repair-venv-paths.py
.\venv\Scripts\pip.exe --version
.\venv\Scripts\pip3.exe --version
.\venv\Scripts\pip3.12.exe --version
.\venv\Scripts\uvicorn.exe --version
```

`pip3.12.exe`는 Python 3.12 기준입니다. 복구 스크립트는 실행 중인 Python 버전에 맞는 이름으로 재생성합니다. 폴더 변경 완료 스크립트는 새 폴더에서 재실행하면 즉시 종료하며 서버를 다시 시작하지 않습니다. 복구 후 터미널을 새로 열어 가상환경을 활성화합니다.

브랜딩 제작 전용 PyMuPDF 2.0은 앱 의존성이 아닙니다. 필요할 때 `python -m pip install --target tmp/branding-tools pymupdf==2.0`으로 격리 설치하고, PDF 개정 명령을 실행하는 프로세스에만 `PYTHONPATH=tmp/branding-tools`를 설정합니다. 서비스 프로세스에는 이 값을 설정하지 않습니다.
