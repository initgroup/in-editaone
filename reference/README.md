# IN-EDITAONE 참조 자료

`frontend/`, `backend/`, `database/`, `main.py`는 실행 소스입니다. 이 디렉터리는 설치·브랜딩 제작·이전 안내를 위한 참조 자료이며 정적 URL로 공개하지 않습니다.

- `environment/`: 실행 환경 재현에 필요한 의존성 목록과 설치 안내. 루트의 배포용 목록과 함께 유지합니다.
- `branding/`: 새 로고·탭/바탕화면 아이콘의 재생성 코드(`build-logos.mjs`, `build-icons.mjs`), 제공받은 시안, PDF 개정 코드와 원본.
- `demo/`: 초간단에디팅의 가상 예제 CSV 재생성 코드. 배포용 CSV는 `simple-edit/sample.csv`에 둡니다.
- `benchmarks/`: 외부 예제와 현재 엔진의 비교 기록·오프라인 재현 스크립트. 입력 원본은 수정하지 않으며 실행 모델이나 서비스 의존성으로 사용하지 않습니다.
- `BRAND_MIGRATION.md`: 폴더·GitHub·Render·DB 설정의 전환 절차와 검증 결과.

과거 `artifacts/`, `.codex-artifacts/`, `tmp/` 산출물은 실행 소스와 분리된 원본 기록입니다. 이 폴더의 구명칭은 서비스 표시값이 아닙니다.
