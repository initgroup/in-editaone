(function () {
    "use strict";
    const $ = (id) => document.getElementById(id);
    const ko = {
        historyTitle:"과거 실행", historyClose:"닫기", historyNeedsTarget:"메인에서 대상 DB를 선택해 주세요.", historyRunning:"실행 중", historyPaused:"일시정지", historyStopped:"중지", historyLoading:"저장된 실행을 불러오는 중…", historyCount:"퀵 에디팅 실행 {count}건", historyEmpty:"조회할 과거 실행이 없습니다.", historyError:"과거 실행을 불러오지 못했습니다. 새로고침해 주세요.", historyRefresh:"새로고침", historyMore:"이전 실행 더 보기", historyOpen:"핵심 규칙 보기 ↗", historySuccess:"완료", historyFailed:"실패", historyOther:"실행 상태 확인", historyOtherRun:"다른 실행",
        storedResultNote:"퀵 에디팅에 저장된 혼합형 탐지 결과입니다. 다시 분석하지 않습니다. 실패·중단된 실행은 저장된 일부 결과만 표시될 수 있습니다. 위반 0건·미기록 규칙은 제외합니다.",
        storedDetailHelp:"당시 저장된 탐지 집계와 위반 예시입니다. 원본을 다시 조회하거나 학습하지 않습니다. 일치 행은 보관된 위반 예시에 포함되지 않습니다. 그래프·데이터·CSV는 저장된 위반 예시 최대 100개입니다.",
        storedPreview:"저장된 위반 예시 {shown}개 / 탐지 {total}건", storedCase:"데이터 식별값", storedSource:"저장된 탐지 결과", appliedUnknown:"적용 건수 미기록", countsUnknown:"적용·일치 집계가 미기록이거나 불일치합니다. 저장된 위반 데이터에서 확인해 주세요.", historyNoRules:"표시할 저장 규칙이 없어요", historyNoRulesHelp:"이 실행의 혼합형 탐지 결과가 미저장이거나, 위반이 확인된 규칙이 없습니다.",

        mode: "핵심 규칙 찾기", eyebrow: "YOUR DATA. ITS OWN RULES.", title: "수식과 조건,<br><em>핵심만 한눈에.</em>",
        lead: "규칙을 찾고, 어긋난 데이터를 확인하세요.",
        example: "수식 예시", formulaExample: "결제금액 ≈ 상품금액 − 할인금액", choose: "분석할 파일을 선택하세요",
        fileChoose: "파일 선택", fileHint: "휴대폰의 파일도 선택할 수 있어요", headerShort: "첫 행은 컬럼명 · 20MB 이하",
        sample: "예제 CSV 다운로드", formatTitle: "파일 조건과 헤더 예시", formatText: "컬럼명은 한 줄로, 빈 칸·중복 없이 넣어 주세요. Excel은 활성 시트를 읽습니다.",
        minimum: "헤더 제외 32행 이상 · 최소 2컬럼. 최대 100컬럼을 분석하며, 초과해도 앞의 100컬럼만 사용해 실행합니다. 수식 데모에는 200행 이상과 계산 관계가 있는 컬럼을 권장합니다.",
        columnScope: "{source}컬럼 → 앞의 {used}컬럼 분석 ({omitted}개 제외)",
        columnScopeResult: "{source}컬럼 → 앞의 {used}컬럼 분석 ({omitted}개 제외)",
        limits: "최대 20MB·원본 20만 행. 1만 행 이하는 전체, 넘으면 전체 파일에서 최대 1만 행을 무작위로 추출합니다. 긴 텍스트는 셀당 4,000바이트 이하로 제한합니다.",
        run: "분석 시작", login: "메인에서 로그인하기 →", sampling: "최대 10,000행 · 다시 실행하면 표본과 검증 구간을 새로 뽑습니다.",
        loadingLabel:"분석 진행 중", loadingStored:"저장 결과 조회 중", loadingStoredHelp:"선택한 실행의 핵심 규칙을 불러옵니다.", loadingTitle: "규칙과 위반을\n분석하고 있습니다", loadingText: "파일 검사 → 규칙 발굴·검증 → 분석 표본의 위반 탐지", loadingHelp: "파일 크기와 컬럼 수에 따라 시간이 달라집니다.",
        resultEyebrow: "분석 결과", resultTitle: "발견한 핵심 규칙", formula: "수식규칙", condition: "조건규칙", top: "검증 기준을 통과한 규칙 중 유형별 상위 5개까지 보여드립니다.",
        resultNote: "조건규칙·수식규칙 모두 혼합형 패턴으로 발굴합니다. 학습·검증으로 채택한 규칙을 분석 표본 전체(최대 1만 행)에 적용해 위반을 찾습니다. 표본 밖의 행은 검사하지 않습니다. 위반은 확인이 필요한 값이며 확정 오류가 아닙니다. 원본 전체 탐지와 수정은 퀵 에디팅에서 진행하세요.",
        rerun: "다시 분석", newFile: "다른 파일", footer: "조건을 발견하고, 수식을 찾아내다.",
        needLogin: "로그인 후 핵심 규칙 찾기을 이용할 수 있습니다.", network: "서버에 연결할 수 없습니다. 연결 상태를 확인한 뒤 다시 실행해 주세요.",
        fileType: "CSV, TSV, XLSX, XLSM 파일을 선택해 주세요.", fileSize: "비어 있지 않은 20MB 이하 파일을 선택해 주세요.",
        noFormula: "검증된 수식이 아직 없어요", noCondition: "검증된 조건규칙이 아직 없어요",
        noViolations: "위반이 확인된 규칙이 없어요", cleanRules: "분석한 표본에서 발견된 규칙의 위반이 없습니다.",
        emptyFormula: "합계·금액·수량처럼 계산 관계가 있는 컬럼을 함께 넣어 보세요. 규칙을 만들 수 없는 자료도 있습니다.",
        emptyCondition: "여러 행에서 반복되는 분류나 조건이 필요합니다. 다른 표본으로 다시 확인하거나 예제 CSV를 사용해 보세요.",
        source: "원본", sampled: "분석", allRows: "전체 행 사용", randomRows: "균등 무작위 표본", rows: "행", seconds: "초", validation: "검증 일치", validationRows: "검증", support: "학습 충족", applies: "적용 조건", tolerance: "허용오차", noMeasure: "미측정",
        previewLabel: "발견할 수 있는 관계 · 예시", conditionExample: "고객유형 = VIP → 배송비 = 0", previewNote: "실제 규칙은 업로드한 데이터에서 찾아 검증합니다.",
        stepFile: "파일 선택", stepDiscover: "규칙 발굴", stepResult: "핵심 결과", evidence: "검증 정보 보기",
        samplePrompt: "준비된 파일이 없으신가요?", sampleRun: "예제로 바로 체험", samplePreparing: "예제 준비 중…",
        sessionChecking: "로그인 확인 중", sessionConnected: "로그인 연결됨", sessionExpired: "로그인 필요", sessionOffline: "연결 확인 필요",
        fullscreen: "전체 화면", exitFullscreen: "전체 화면 나가기",
        checking: "파일 형식과 데이터 수를 확인하고 있어요…", ready: "검사 완료", columns: "컬럼",
        busy: "핵심 규칙 찾기 분석을 마친 뒤 화면을 닫아 주세요.", targetLimit: "빠른 탐색 범위: 조건 대상 최대 24개 · 수식 대상 최대 12개",
        analysisInfo:"분석 정보 ⓘ", openRule:"상세 보기 ↗", moreRules:"규칙 {count}개 더 보기", lessRules:"핵심 3개만 보기", backResults:"← 핵심 결과",
        graph:"그래프", data:"데이터", metricHelp:"탐지·검증 기준 ⓘ", checkedRows:"적용한 행", matchRate:"일치율", match:"일치", different:"위반", all:"전체", unscorable:"위반 · 계산 불가",
        detailHelp:"채택한 규칙을 다시 학습하지 않고 분석 표본 전체에 적용했습니다. 적용 조건을 충족하면서 결과가 다르거나 계산 불가인 행을 위반으로 표시합니다. 확정 오류는 아닙니다. 상세는 일치·위반에서 고른 최대 120행입니다. 원본 순번은 헤더·빈 행을 제외하며 긴 셀은 160자까지만 표시합니다.",
        validationDetail:"선택 검증: {rate}% 일치 · {count}행 (규칙 선택용, 전체 정확도 아님)",
        violationsShort:"위반 {count}", appliedShort:"{count}행 적용", ruleDetection:"위반 {count} · 적용 {total}행", detectionHint:"분석 표본에서 이 규칙에 해당하는 행을 검사한 결과입니다. 상세에서 위반 값을 확인하세요.",
        expected:"계산값", actual:"실제값", residual:"차이", sourceRow:"원본 순번", rowStatus:"판정", previous:"이전", next:"다음", downloadData:"상세표본 CSV ↓",
        formulaGraph:"계산값과 실제값 비교", conditionGraph:"규칙에 맞는 행과 위반한 행", pointHint:"점 선택 → 입력값 확인. 방향키로 이동할 수 있습니다.", barHint:"막대 선택 → 데이터 확인",
        graphScope:"적용 {total}행 중 {shown}개 · 점을 눌러보세요",
        noDetail:"상세 데이터가 없습니다. 다시 분석해 주세요.", noNumericPoints:"숫자로 비교할 수 있는 상세 표본이 없습니다.", noRows:"해당 데이터가 없습니다.",
        detailScope:"적용 {total}행 중 상세 표본 {shown}개", clippedCells:"긴 셀 일부는 생략했습니다."
    };
    const en = {
        historyTitle:"Past runs", historyClose:"Close", historyNeedsTarget:"Select a Target DB in the main window.", historyRunning:"Running", historyPaused:"Paused", historyStopped:"Stopped", historyLoading:"Loading saved runs…", historyCount:"{count} Quick Editing runs", historyEmpty:"No past runs are available.", historyError:"Unable to load past runs. Refresh to retry.", historyRefresh:"Refresh", historyMore:"Load earlier runs", historyOpen:"View key rules ↗", historySuccess:"Completed", historyFailed:"Failed", historyOther:"Check run status", historyOtherRun:"Other runs",
        storedResultNote:"Stored mixed-pattern detection from Quick Editing. No analysis is rerun. Failed or stopped runs may contain partial results. Zero or unrecorded violation counts are excluded.",
        storedDetailHelp:"Stored detection totals and violation examples from this run. The source is not queried or fitted again. Matching rows are not included in these saved violation examples. Charts, data and CSV contain up to 100 saved violations.",
        storedPreview:"{shown} saved examples / {total} detected violations", storedCase:"Data identifier", storedSource:"Stored detection results", appliedUnknown:"Applicable count unrecorded", countsUnknown:"Applicable/matching totals are missing or inconsistent. Review the stored violation data.", historyNoRules:"No stored rules to display", historyNoRulesHelp:"Mixed detection results were not saved for this run, or no rules with recorded violations are available.",

        mode: "Find Key Rules", eyebrow: "YOUR DATA. ITS OWN RULES.", title: "Formulas. Conditions.<br><em>Just the essentials.</em>", lead: "Discover rules. Find the values that break them.",
        example: "Formula example", formulaExample: "Payment ≈ Amount − Discount", choose: "Choose a file to explore", fileChoose: "Choose a file", fileHint: "Choose from Files on your phone, too", headerShort: "Column names first · Up to 20 MB",
        sample: "Download example CSV", formatTitle: "File limits and header example", formatText: "Use one header row with unique, nonempty column names. Excel uses the active sheet.",
        minimum: "At least 32 data rows and 2 columns. Up to 100 columns are analyzed; wider files still run using the first 100. For a formula demo, 200+ rows with related calculation columns are recommended.",
        columnScope: "{source} columns → first {used} analyzed ({omitted} excluded)",
        columnScopeResult: "{source} columns → first {used} analyzed ({omitted} excluded)",
        limits: "Up to 20 MB and 200,000 source rows. All rows up to 10,000; otherwise a uniform random sample from the entire file. Text cells: up to 4,000 UTF-8 bytes.",
        run: "Start analysis", login: "Sign in from the main page →", sampling: "Up to 10,000 rows · Every run draws a fresh sample and validation split.",
        loadingLabel:"Analysis in progress", loadingStored:"Loading saved results", loadingStoredHelp:"Retrieving key rules from the selected run.", loadingTitle: "Discovering rules.\nChecking violations.", loadingText: "Check file → Discover and validate rules → Detect sample violations", loadingHelp: "Time varies with file size and number of columns.",
        resultEyebrow: "ANALYSIS RESULTS", resultTitle: "The key discoveries", formula: "Formulas", condition: "Conditions", top: "Up to 5 leading rules of each type that passed validation.",
        resultNote: "Condition and formula rules both use mixed pattern discovery. Accepted rules are applied to the full analyzed sample of up to 10,000 rows. Rows outside that sample are not checked. Violations need review; they are not confirmed errors. Use Quick Editing for full-source detection and editing.",
        rerun: "Run again", newFile: "Another file", footer: "Discover conditions. Uncover formulas.",
        needLogin: "Sign in to use Find Key Rules.", network: "Unable to connect. Check your connection and try again.", fileType: "Choose a CSV, TSV, XLSX or XLSM file.", fileSize: "Choose a nonempty file up to 20 MB.",
        noFormula: "No validated formulas yet", noCondition: "No validated conditions yet", emptyFormula: "Include columns with calculation relationships, such as amounts, quantities and totals. Some data does not contain a validated formula.",
        noViolations: "No rules with detected violations", cleanRules: "No violations of the discovered rules were found in the analyzed sample.",
        emptyCondition: "Look for categories and conditions that repeat across rows. Try a fresh sample or the example CSV.", source: "Source", sampled: "Analyzed", allRows: "All source rows", randomRows: "Uniform random sample", rows: "rows", seconds: "s", validation: "Validation match", validationRows: "Checked", support: "Training matches", applies: "Applies when", tolerance: "Tolerance", noMeasure: "Unavailable",
        previewLabel: "Relationships you can discover · EXAMPLE", conditionExample: "Customer = VIP → Shipping fee = 0", previewNote: "Real rules are discovered and validated from your file.",
        stepFile: "Choose file", stepDiscover: "Discover", stepResult: "Highlights", evidence: "View validation details",
        samplePrompt: "No file on hand?", sampleRun: "Try the live example", samplePreparing: "Preparing example…",
        sessionChecking: "Checking sign-in", sessionConnected: "Session connected", sessionExpired: "Sign-in required", sessionOffline: "Check connection",
        fullscreen: "Full screen", exitFullscreen: "Exit full screen",
        checking: "Checking file format and data rows…", ready: "File checked", columns: "columns",
        busy: "Wait for Find Key Rules to finish before closing this page.", targetLimit: "Fast search: up to 24 condition targets and 12 formula targets",
        analysisInfo:"Analysis info ⓘ", openRule:"Details ↗", moreRules:"Show {count} more rules", lessRules:"Show top 3 only", backResults:"← Key results",
        graph:"Graph", data:"Data", metricHelp:"Detection & validation ⓘ", checkedRows:"Applicable rows", matchRate:"Match rate", match:"Match", different:"Violations", all:"All", unscorable:"Violation · Not calculable",
        detailHelp:"Frozen rules are applied to the whole analyzed sample without refitting. Applicable rows with a different or unscorable result are violations, not confirmed errors. Details contain up to 120 records sampled separately from matches and violations. Source order excludes headers and blank rows. Long cells are limited to 160 characters.",
        validationDetail:"Selection validation: {rate}% match · {count} rows (used for rule selection, not population accuracy)",
        violationsShort:"{count} violations", appliedShort:"{count} rows", ruleDetection:"{count} violations · {total} applicable rows", detectionHint:"Checked applicable rows in the analyzed sample. Open details to review the violating values.",
        expected:"Calculated", actual:"Actual", residual:"Difference", sourceRow:"Source order", rowStatus:"Status", previous:"Previous", next:"Next", downloadData:"Detail sample CSV ↓",
        formulaGraph:"Calculated vs actual", conditionGraph:"Matching and violating rows", pointHint:"Select a point for its input values. Use arrow keys for keyboard navigation.", barHint:"Select a bar to explore those rows.",
        graphScope:"{shown} of {total} applicable rows · Select a point",
        noDetail:"No detail data. Run the analysis again.", noNumericPoints:"No numeric detail points to compare.", noRows:"No rows in this view.",
        detailScope:"{shown} detail records from {total} applicable rows", clippedCells:"Some long cells were shortened."
    };
    let verifiedTarget = null;
    let language = "ko", file = null, result = null, busy = false, authenticated = false, verifiedUser = null;
    let controller = null, timer = null, requestVersion = 0, family = "FORMULA";
    let preflightController = null, preflightVersion = 0, preflight = null, checking = false;
    let sessionPromise = null, sessionController = null, sessionTimer = null, heartbeatMs = 90000;
    let sessionState = "checking", destroyed = false, errorKind = "";
    let sampleController = null, loadingSample = false;
    let currentView = "input", detailRule = null, returnScroll = 0, returnFocus = "";
    const expandedFamilies = new Set();
    const t = (key) => (language === "en" ? en : ko)[key] || key;
    const number = (value) => new Intl.NumberFormat(language === "en" ? "en-US" : "ko-KR", {maximumFractionDigits: 2}).format(Number(value));
    const text = (id, value) => { $(id).textContent = value; };
    const details = window.RuleDiscoveryDetails({t, number, onBack: () => closeRuleDetail()});
    const historyUI = window.KeyRuleHistory({t, context:() => ({user:verifiedUser, target:verifiedTarget}),
        onSelect:loadHistoryResult, onExpired:invalidateSession, onConflict:() => {clearWork(); checkSession();}});
    const isStored = () => result?.detectionScope === "STORED_TARGET";
    function isDetection(detail) {return ["ANALYZED_SAMPLE","STORED_DETECTION"].includes(detail?.cohort);}
    async function storedRequest(path) {
        if (!authenticated || !verifiedTarget || busy) throw new Error(t("historyError"));
        const ticket = ++requestVersion; const target = verifiedTarget;
        busy = true; controller?.abort(); controller = new AbortController();
        const timeout = setTimeout(() => controller?.abort(),45000);
        renderFile(); show("loading", true); text("se-elapsed", "");
        try {
            const response = await fetch(path,{credentials:"include",cache:"no-store",headers:{"X-Target-Connection-Id":String(target)},signal:controller.signal});
            if (ticket !== requestVersion || target !== verifiedTarget || destroyed) throw new DOMException("Cancelled","AbortError");
            if ([401,403].includes(response.status)) {invalidateSession(); throw new DOMException("Expired","AbortError");}
            const payload = await response.json().catch(() => ({}));
            if (ticket !== requestVersion || target !== verifiedTarget || destroyed) throw new DOMException("Cancelled","AbortError");
            if (response.status === 409) {clearWork(); checkSession(); throw new Error(typeof payload.detail === "string" ? payload.detail : t("historyError"));}
            if (!response.ok || payload.status !== "success") throw new Error(typeof payload.detail === "string" ? payload.detail : t("historyError"));
            return {data:payload.data,ticket};
        } finally {
            clearTimeout(timeout);
            if (ticket === requestVersion) {busy = false; controller = null; show(result ? "results" : "input"); renderFile();}
        }
    }
    async function loadHistoryResult(runId) {
        preflightController?.abort(); ++preflightVersion; checking = false;
        const response = await storedRequest(`/api/M00002/history/${runId}`);
        if (response.ticket !== requestVersion) return;
        if (response.data?.detectionScope !== "STORED_TARGET" || !response.data?.rules) throw new Error(t("historyError"));
        result = response.data; file = null; preflight = null; family = "FORMULA";
        expandedFamilies.clear(); details.clear(); clearDetailHistory(); error(""); renderResults(true);
    }
    function readLanguage() {
        try {
            const host = window.parent !== window ? window.parent : window.opener;
            const hostLanguage = host && host.location.origin === location.origin ? host.I18nManager?.getCurrentLanguage?.() : null;
            language = String(hostLanguage || new URLSearchParams(location.search).get("lang") || sessionStorage.getItem("initLanguageCode") || "ko").startsWith("en") ? "en" : "ko";
        } catch (_) { language = "ko"; }
    }
    function applyLanguage() {
        readLanguage();
        document.documentElement.lang = language;
        document.title = `${t("mode")} · IN-EDITAONE Demo`;
        document.querySelectorAll("[data-i18n]").forEach((element) => {
            const value = t(element.dataset.i18n);
            if (["title", "lead"].includes(element.dataset.i18n)) element.innerHTML = value;
            else element.textContent = value;
        });
        renderFile(); historyUI.refresh();
        renderSession(); updateFullscreen();
        if (currentView === "loading") renderLoading(document.body.dataset.loadingKind === "stored");
        if (result && !busy) {
            if (currentView === "detail" && detailRule) details.refresh();
            else renderResults(false);
        }
    }
    function error(message, needsLogin = false, kind = "file") {
        errorKind = message ? kind : "";
        text("se-result-error",message); $("se-result-error").hidden = !message;
        text("se-error", message);
        $("se-error").hidden = !message;
        $("se-login").hidden = !needsLogin;
    }
    function renderFile() {
        $("se-history-open").title = t(authenticated && !verifiedTarget ? "historyNeedsTarget" : "historyTitle"); $("se-history-open").setAttribute("aria-label", t("historyTitle"));
        historyUI.setEnabled(authenticated && Boolean(verifiedTarget) && !busy && !checking && !loadingSample);
        text("se-file-name", file?.name || t("fileChoose"));
        text("se-file-meta", file ? `${number(file.size / 1024 / 1024)} MB` : t("fileHint"));
        $("se-run").disabled = !file || busy || checking || loadingSample || !preflight || !authenticated;
        $("se-file").disabled = busy || loadingSample;
        $("se-sample-run").disabled = busy || checking || loadingSample || !authenticated;
        $("se-sample-run").querySelector("[data-i18n]").textContent = t(loadingSample ? "samplePreparing" : "sampleRun");
        text("se-file-check", checking ? t("checking") : preflight ? `${t("ready")} · ${number(preflight.sourceRows)} ${t("rows")} · ${preflight.columns} ${t("columns")}` : "");
        $("se-file-check").hidden = !checking && !preflight;
        renderColumnNotice("se-column-notice", preflight);
    }
    function renderColumnNotice(id, data, completed = false) {
        const source = Number(data?.sourceColumns ?? data?.columns ?? 0);
        const used = Number(data?.columns ?? 0);
        const omitted = Math.max(0, source - used);
        text(id, omitted ? t(completed ? "columnScopeResult" : "columnScope").replace("{source}", number(source)).replace("{used}", number(used)).replace("{omitted}", number(omitted)) : "");
        $(id).hidden = !omitted;
    }
    async function chooseFile(selected) {
        if (!selected || busy || destroyed) return false;
        preflightController?.abort(); ++preflightVersion; preflight = null; checking = false;
        result = null;
        if (!/\.(csv|tsv|xlsx|xlsm)$/i.test(selected.name)) { file = null; error(t("fileType")); }
        else if (!selected.size || selected.size > 20 * 1024 * 1024) { file = null; error(t("fileSize")); }
        else { file = selected; error(authenticated ? "" : t("needLogin"), !authenticated); }
        renderFile();
        if (file && authenticated) return inspectFile();
        return false;
    }
    async function inspectFile() {
        const version = ++preflightVersion;
        preflightController = new AbortController(); checking = true; renderFile();
        try {
            const body = new FormData(); body.append("file", file);
            const response = await fetch("/api/M00002/preflight", {method: "POST", credentials: "include", body, signal: preflightController.signal});
            const payload = await response.json().catch(() => ({}));
            if (version !== preflightVersion) return;
            if (response.status === 401 || response.status === 403) { invalidateSession(); return false; }
            if (!response.ok || payload.status !== "success") throw new Error(typeof payload.detail === "string" ? payload.detail : payload.detail?.message || t("network"));
            preflight = payload.data;
            shareSession(response); return true;
        } catch (failure) {
            if (failure.name !== "AbortError" && version === preflightVersion) error(failure.message || t("network"), !authenticated);
        } finally {
            if (version === preflightVersion) { checking = false; preflightController = null; renderFile(); }
        }
        return false;
    }
    function renderSession() {
        $("se-session").dataset.state = sessionState;
        text("se-session-text", t({checking: "sessionChecking", connected: "sessionConnected", expired: "sessionExpired", offline: "sessionOffline"}[sessionState]));
    }
    function shareSession(response) {
        for (const host of [window.parent !== window ? window.parent : null, window.opener]) {
            try {
                if (host && !host.closed && host.location.origin === location.origin
                    && String(host.PageManager?.getLoginUser?.().userId || "") === verifiedUser) {
                    host.PageManager.extendSessionFromResponse(response);
                }
            } catch (_) { /* The main window may already be closed or on another origin. */ }
        }
    }
    function clearWork() {
        ++requestVersion; ++preflightVersion; historyUI.reset();
        controller?.abort(); preflightController?.abort(); sampleController?.abort(); stopTimer();
        busy = false; checking = false; loadingSample = false; file = null; result = null; preflight = null;
        detailRule = null; details.clear(); expandedFamilies.clear(); clearDetailHistory();
        $("se-file").value = "";
        $("se-rules-formula").replaceChildren(); $("se-rules-condition").replaceChildren();
        text("se-result-file", ""); $("se-summary").replaceChildren();
        renderColumnNotice("se-result-column-notice", null);
        show("input"); renderFile();
    }
    function invalidateSession() {
        authenticated = false; sessionState = "expired"; clearWork();
        error(t("needLogin"), true, "auth"); renderSession();
    }
    function scheduleSessionCheck() {
        clearTimeout(sessionTimer);
        if (destroyed || sessionState === "expired") return;
        sessionTimer = setTimeout(() => {
            if (document.visibilityState === "visible" || busy) checkSession();
            else scheduleSessionCheck();
        }, heartbeatMs);
    }
    function checkSession() {
        if (destroyed) return Promise.resolve(false);
        if (sessionPromise) return sessionPromise;
        sessionPromise = (async () => {
            sessionController = new AbortController();
            const timeout = setTimeout(() => sessionController?.abort(), 10000);
            try {
                const response = await fetch("/api/M00002/session", {credentials: "include", cache: "no-store", signal: sessionController.signal});
                if (destroyed) return false;
                if (response.status === 401 || response.status === 403) { invalidateSession(); return false; }
                if (!response.ok) throw new Error(t("network"));
                const session = await response.json();
                if (destroyed) return false;
                const user = String(session.user?.userId || "");
                if (!user) throw new Error(t("network"));
                const target = Number(session.targetConnectionId) || null;
                if (verifiedUser && (verifiedUser !== user || verifiedTarget !== target)) clearWork();
                verifiedTarget = target;
                verifiedUser = user; authenticated = true; sessionState = "connected";
                heartbeatMs = Math.min(90000, Math.max(15000, (Number(session.sessionTtlSeconds) || 3600) * 1000 / 3));
                if (errorKind === "auth" || errorKind === "network") error("");
                shareSession(response);
                if (file && !preflight && !checking && !errorKind) inspectFile();
                return true;
            } catch (_) {
                if (!destroyed) {
                    sessionState = "offline";
                    if (!authenticated) error(t("network"), false, "network");
                }
                return false;
            } finally {
                clearTimeout(timeout); sessionController = null;
                if (!destroyed) { renderSession(); renderFile(); }
            }
        })().finally(() => { sessionPromise = null; scheduleSessionCheck(); });
        return sessionPromise;
    }
    function renderLoading(stored) {
        document.body.dataset.loadingKind = stored ? "stored" : "analysis";
        text("se-loading-title",t(stored ? "loadingStored" : "loadingTitle"));
        text("se-loading-help",t(stored ? "loadingStoredHelp" : "loadingHelp"));
        text("se-loading-label",t(stored ? "historyLoading" : "loadingLabel"));
    }
    function show(view, stored = false) {
        currentView = view;
        if (view === "loading") renderLoading(stored);
        document.body.dataset.view = view;
        document.querySelectorAll("[data-step]").forEach(step => {
            if (step.dataset.step === view) step.setAttribute("aria-current", "step");
            else step.removeAttribute("aria-current");
        });
        $("se-intro").hidden = view !== "input";
        $("se-input-panel").hidden = view !== "input";
        $("se-loading").hidden = view !== "loading";
        $("se-results").hidden = view !== "results";
        $("se-detail").hidden = view !== "detail";
    }
    function stopTimer() { window.clearInterval(timer); timer = null; }
    async function runSample() {
        if (busy || checking || loadingSample || !authenticated || destroyed) return;
        const version = requestVersion;
        loadingSample = true; sampleController = new AbortController(); error(""); renderFile();
        try {
            const response = await fetch("./sample.csv", {signal: sampleController.signal});
            if (!response.ok) throw new Error(t("network"));
            const blob = await response.blob();
            if (destroyed || version !== requestVersion) return;
            const selected = new File([blob], language === "en" ? "IN-EDITAONE_demo.csv" : "인에디타원_데모_거래.csv", {type: "text/csv"});
            if (await chooseFile(selected)) await run();
        } catch (failure) {
            if (failure.name !== "AbortError" && version === requestVersion && !destroyed) error(failure.message || t("network"));
        } finally {
            loadingSample = false; sampleController = null;
            if (!destroyed) renderFile();
        }
    }
    async function run() {
        if (!file || busy || checking || !preflight || !authenticated) return;
        busy = true;
        result = null;
        detailRule = null; details.clear(); expandedFamilies.clear(); clearDetailHistory();
        const version = ++requestVersion;
        controller = new AbortController();
        renderFile(); error(""); show("loading");
        const started = performance.now();
        const tick = () => text("se-elapsed", `${Math.floor((performance.now() - started) / 1000)}${t("seconds")}`);
        tick(); timer = window.setInterval(tick, 1000);
        window.scrollTo({top: 0, behavior: "instant"});
        try {
            const body = new FormData(); body.append("file", file);
            const response = await fetch("/api/M00002/analyze", {method: "POST", credentials: "include", body, signal: controller.signal});
            const payload = await response.json().catch(() => ({}));
            if (version !== requestVersion) return;
            if (response.status === 401 || response.status === 403) { invalidateSession(); return; }
            if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : payload.detail?.message || t("network"));
            if (payload.status !== "success" || !payload.data?.rules) throw new Error(t("network"));
            shareSession(response);
            result = payload.data; family = "FORMULA";
            renderResults(true);
        } catch (failure) {
            if (failure.name === "AbortError" || version !== requestVersion) return;
            show("input");
            error(failure.message || t("network"), !authenticated);
        } finally {
            if (version === requestVersion) { busy = false; controller = null; stopTimer(); renderFile(); }
        }
    }
    function element(tag, className, value) {
        const node = document.createElement(tag); node.className = className;
        if (value != null) node.textContent = value;
        return node;
    }
    function visibleRules(kind) {
        return (result?.rules[kind] || []).filter(rule => isDetection(rule.detail) && Number(rule.detail.stats?.different) > 0).slice(0, 5);
    }
    function renderRules(kind) {
        const target = $(kind === "FORMULA" ? "se-rules-formula" : "se-rules-condition");
        target.replaceChildren();
        const available = visibleRules(kind);
        const primary = [], repeated = [], seen = new Set();
        for (const rule of available) {
            const keys = rule.detail?.target ? [...new Set([rule.detail.target.key, ...rule.detail.inputs.map(column => column.key)])].sort().join("|") : rule.id;
            (seen.has(keys) ? repeated : primary).push(rule); seen.add(keys);
        }
        const allRules = [...primary, ...repeated];
        const rules = expandedFamilies.has(kind) ? allRules : allRules.slice(0, 3);
        text(kind === "FORMULA" ? "se-count-formula" : "se-count-condition", allRules.length);
        if (!allRules.length) {
            const empty = element("div", "se-empty");
            const discovered = Number(result.discoveredCounts?.[kind]) > 0;
            empty.append(element("strong", "", t(isStored() ? "historyNoRules" : discovered ? "noViolations" : kind === "FORMULA" ? "noFormula" : "noCondition")), element("p", "", t(isStored() ? "historyNoRulesHelp" : discovered ? "cleanRules" : kind === "FORMULA" ? "emptyFormula" : "emptyCondition")));
            target.append(empty); return;
        }
        rules.forEach((rule, index) => {
            const card = element("article", "se-rule-card");
            const rank = element("span", "se-rule-rank", String(index + 1).padStart(2,"0"));
            rank.setAttribute("aria-hidden", "true");
            const content = element("div", "se-rule-content");
            const heading = element("h3", "se-rule-equation", rule.result);
            const condition = element("p", "se-rule-condition", `${t("applies")} · ${rule.condition}`); condition.title = rule.condition;
            const footer = element("div", "se-rule-footer");
            const stats = isDetection(rule.detail) ? rule.detail.stats : null;
            const match = element("span", `se-rule-match${stats?.different ? " has-violations" : ""}`);
            if (stats) match.append(element("span", "se-rule-violations", t("violationsShort").replace("{count}", number(stats.different))),
                element("span", "se-rule-applied", stats.applied == null ? t("appliedUnknown") : t("appliedShort").replace("{count}", number(stats.applied))));
            else match.textContent = t("noMeasure");
            match.title = t("detectionHint");
            const button = element("button", "se-rule-open", t("openRule")); button.type = "button";
            button.id = `se-rule-open-${kind}-${index}`;
            button.addEventListener("click", () => openRuleDetail(rule, kind, button.id));
            footer.append(match, button);
            if (kind === "CONDITION") content.append(condition, heading);
            else { content.append(heading); if (rule.hasCondition !== false) content.append(condition); }
            heading.title = rule.result;
            button.title = `${rule.result}\n${rule.condition}`;
            button.setAttribute("aria-label", `${t("openRule")} · ${rule.result}`);
            card.append(rank, content, footer); target.append(card);
        });
    }
    function updateMore() {
        const count = visibleRules(family).length;
        $("se-more").hidden = count <= 3;
        text("se-more", expandedFamilies.has(family) ? t("lessRules") : t("moreRules").replace("{count}", count - 3));
    }
    function activateFamily(next, focus = false) {
        family = next;
        document.querySelectorAll("[data-family]").forEach((button) => {
            const selected = button.dataset.family === next;
            button.setAttribute("aria-selected", String(selected)); button.tabIndex = selected ? 0 : -1;
            if (selected && focus) button.focus();
        });
        $("se-rules-formula").hidden = next !== "FORMULA";
        $("se-rules-condition").hidden = next !== "CONDITION";
        updateMore();
    }
    function renderResults(focus) {
        show("results");
        $("se-rerun").hidden = isStored(); $("se-history-other").hidden = !isStored();
        document.querySelector('[data-i18n="resultNote"]').textContent = t(isStored() ? "storedResultNote" : "resultNote");
        text("se-result-file", isStored() ? [result.history.project,result.history.scenario,result.history.targetTable].filter(Boolean).join(" · ") : file?.name || "");
        $("se-summary").replaceChildren(...(isStored() ? [`#${result.history.flowRunId}`,t("storedSource")] : [
            `${t("source")} ${number(result.sourceRows)} ${t("rows")}`,
            `${t("sampled")} ${number(result.sampleRows)} ${t("rows")}`,
            result.sourceRows > result.sampleRows ? t("randomRows") : t("allRows"),
            `${number(result.elapsedSeconds)}${t("seconds")}`
        ]).map((value) => element("span", "", value)));
        renderRules("FORMULA"); renderRules("CONDITION"); activateFamily(family);
        renderColumnNotice("se-result-column-notice", result, true);
        if (focus) { window.scrollTo({top: 0, behavior: "instant"}); $("se-result-title").focus({preventScroll: true}); }
    }
    function clearDetailHistory() {
        if (location.hash.startsWith("#rule-")) {
            try { history.replaceState(null, "", location.pathname + location.search); } catch (_) { /* closing document */ }
        }
    }
    async function openRuleDetail(rule, kind, focusId, push = true) {
        if (!result || busy) return;
        if (isStored() && !rule.detail.loaded) {
            try {
                const response = await storedRequest(`/api/M00002/history/${result.history.flowRunId}?ruleKey=${encodeURIComponent(rule.storedRuleKey)}`);
                if (response.ticket !== requestVersion) return;
                if (response.data?.storedRuleKey !== rule.storedRuleKey || response.data?.detail?.cohort !== "STORED_DETECTION") throw new Error(t("historyError"));
                Object.assign(rule,response.data); error("");
            } catch (failure) {if (failure.name !== "AbortError") error(failure.message || t("historyError")); return;}
        }
        if (currentView !== "detail") { returnScroll = window.scrollY; returnFocus = focusId || ""; }
        family = kind; detailRule = rule; details.show(rule); show("detail");
        if (push) history.pushState({ruleId:rule.id, family:kind}, "", `#rule-${encodeURIComponent(rule.id)}`);
        window.scrollTo({top:0, behavior:"instant"}); $("se-detail-title").focus({preventScroll:true});
    }
    function closeRuleDetail(fromHistory = false) {
        if (!result) return;
        if (!fromHistory && history.state?.ruleId === detailRule?.id && location.hash.startsWith("#rule-")) { history.back(); return; }
        detailRule = null; details.clear(); renderResults(false);
        requestAnimationFrame(() => { window.scrollTo({top:returnScroll, behavior:"instant"}); $(returnFocus)?.focus({preventScroll:true}); });
    }
    function reset() {
        if (busy) return;
        clearWork(); error("");
    }
    function destroy() {
        destroyed = true; clearTimeout(sessionTimer); sessionController?.abort(); clearWork();
    }
    function updateFullscreen() {
        $("se-fullscreen").hidden = !document.fullscreenEnabled;
        $("se-fullscreen").setAttribute("aria-pressed", String(Boolean(document.fullscreenElement)));
        text("se-fullscreen-label", t(document.fullscreenElement ? "exitFullscreen" : "fullscreen"));
        $("se-fullscreen").title = $("se-fullscreen-label").textContent;
        $("se-fullscreen").setAttribute("aria-label", $("se-fullscreen-label").textContent);
    }
    function returnToMain(event) {
        try {
            if (window.opener && !window.opener.closed && window.opener.location.origin === location.origin) {
                event.preventDefault(); window.opener.focus();
                if (!authenticated) window.opener.PageManager?.validateServerSession?.();
            }
        } catch (_) { /* Normal same-server navigation remains available. */ }
    }
    $("se-file").addEventListener("change", (event) => { chooseFile(event.target.files?.[0]); event.target.value = ""; });
    $("se-run").addEventListener("click", run);
    $("se-rerun").addEventListener("click", run);
    $("se-history-other").addEventListener("click", () => historyUI.open());
    $("se-new").addEventListener("click", () => { reset(); $("se-file").click(); });
    $("se-sample-run").addEventListener("click", runSample);
    $("se-more").addEventListener("click", () => {
        if (expandedFamilies.has(family)) expandedFamilies.delete(family); else expandedFamilies.add(family);
        renderRules(family); updateMore();
    });
    $("se-fullscreen").addEventListener("click", async () => {
        try {
            if (document.fullscreenElement) await document.exitFullscreen();
            else await document.documentElement.requestFullscreen();
        } catch (_) { updateFullscreen(); }
    });
    document.addEventListener("fullscreenchange", updateFullscreen);
    $("se-login").addEventListener("click", returnToMain);
    document.querySelector(".se-brand").addEventListener("click", returnToMain);
    document.querySelectorAll("[data-family]").forEach((button) => {
        button.addEventListener("click", () => activateFamily(button.dataset.family));
        button.addEventListener("keydown", (event) => {
            if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
                event.preventDefault(); activateFamily(event.key === "Home" ? "FORMULA" : event.key === "End" ? "CONDITION" : family === "FORMULA" ? "CONDITION" : "FORMULA", true);
            }
        });
    });
    window.addEventListener("beforeunload", (event) => { if (busy || loadingSample) { event.preventDefault(); event.returnValue = ""; } });
    window.addEventListener("pagehide", destroy);
    window.addEventListener("popstate", event => {
        if (!result) return;
        const kind = event.state?.family;
        const rule = kind && result.rules[kind]?.find(rule => rule.id === event.state?.ruleId);
        if (rule && location.hash.startsWith("#rule-")) openRuleDetail(rule, kind, "", false);
        else closeRuleDetail(true);
    });
    window.addEventListener("pageshow", event => { if (event.persisted) { destroyed = false; applyLanguage(); checkSession(); } });
    window.addEventListener("focus", () => { if (!destroyed) { applyLanguage(); checkSession(); } });
    document.addEventListener("visibilitychange", () => { if (!destroyed && document.visibilityState === "visible") checkSession(); });
    window.SimpleEditing = {onShow() { applyLanguage(); return checkSession(); }, destroy, getLifecycleState: () => ({canClose: !busy && !loadingSample, message: t("busy")})};
    applyLanguage(); checkSession();
})();
