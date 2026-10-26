const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const {chromium} = require("playwright");
const root = path.resolve(__dirname, "../..");
const origin = "http://simple-edit.test";
const sampleFile = path.join(root, "simple-edit/sample.csv");
const example = () => ({status: "success", data: {sourceRows: 24000, sampleRows: 10000, elapsedSeconds: 2.5,
    rules: Object.fromEntries(["FORMULA", "CONDITION"].map(kind => [kind, Array.from({length: 7}, (_, i) => ({
        id: kind + i, kind, result: kind === "FORMULA" ? "결제금액 ≈ (상품금액 - 할인금액)" : "배송유형 = 무료배송",
        condition: kind === "FORMULA" ? "상품금액 값 있음 그리고 할인금액 값 있음" : "고객유형 = VIP",
        validationConfidence: 1, validationRows: 800, supportRows: 3000, absoluteTolerance: kind === "FORMULA" ? .001 : null,
        detail:{cohort:"ANALYZED_SAMPLE",scannedRows:10000,stats:{applied:3200,matched:3192,different:8,unscorable:0},
            validationCohort:"SELECTION_VALIDATION",validationStats:{applied:800,matched:800,different:0,unscorable:0},
            target:{key:"C003",label:kind === "FORMULA" ? "결제금액" : "배송유형"},
            inputs:kind === "FORMULA" ? [{key:"C001",label:"상품금액"},{key:"C002",label:"할인금액"}] : [{key:"C001",label:"고객유형"}],
            rows:Array.from({length:120}, (_, index) => ({id:index,sourceRow:index + 100,status:index < 8 ? "DIFFERENT" : "MATCH",
                expected:kind === "FORMULA" ? 100 + index * 10 : null, actual:kind === "FORMULA" ? 100 + index * 10 + (index < 8 ? 20 : 0) : null,
                residual:kind === "FORMULA" ? (index < 8 ? 20 : 0) : null,
                values:kind === "FORMULA" ? {C001:String(110 + index * 10),C002:"10",C003:String(100 + index * 10 + (index < 8 ? 20 : 0))} : {C001:"VIP",C003:index < 8 ? "일반배송" : "무료배송"}})),shownRows:120,rowLimit:120}
    }))]))}});

async function open(width = 390, language = "ko", options = {}) {
    const browser = await chromium.launch({headless: true});
    const page = await browser.newPage({viewport: {width, height: 844}, isMobile: width < 700, hasTouch: width < 700});
    const calls = [], errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.addInitScript(language => sessionStorage.setItem("initLanguageCode", language), language);
    await page.route("**/*", async route => {
        const url = new URL(route.request().url());
        if (url.origin !== origin) return route.fulfill({status: 404, body: ""});
        if (url.pathname.startsWith("/api/")) {
            calls.push(url.pathname);
            if (url.pathname === "/api/M00002/session") {
                if (options.session) return options.session(route);
                return route.fulfill({status: options.loggedOut ? 401 : 200, json: {user: {userId: 7}, sessionTtlSeconds: 3600}});
            }
            if (url.pathname.startsWith("/api/M00002/history") && options.history) return options.history(route,url);
            if (url.pathname.endsWith("/preflight")) {
                if (options.preflight) return options.preflight(route);
                return route.fulfill({json: {status: "success", data: {sourceRows: 2400, sampleRows: 2400, columns: 8}}});
            }
            if (url.pathname.endsWith("/analyze")) {
                if (options.analyze) return options.analyze(route);
                return route.fulfill({json: example()});
            }
            return route.fulfill({status: 404, body: ""});
        }
        const local = url.pathname.startsWith("/assets/") ? path.join(root, "frontend", url.pathname)
            : path.join(root, url.pathname, url.pathname.endsWith("/") ? "index.html" : "");
        if (!local.startsWith(root + path.sep) || !fs.existsSync(local) || !fs.statSync(local).isFile()) return route.fulfill({status: 404, body: ""});
        return route.fulfill({contentType: {".html":"text/html", ".css":"text/css", ".js":"application/javascript", ".csv":"text/csv", ".png":"image/png"}[path.extname(local)], body: fs.readFileSync(local)});
    });
    await page.goto(origin + "/simple-edit/");
    await page.waitForFunction(() => window.SimpleEditing);
    return {browser, page, calls, errors};
}

async function choose(page) {
    await page.locator("#se-file").setInputFiles(sampleFile);
    await page.waitForFunction(() => !document.querySelector("#se-run").disabled);
}

for (const [width, language] of [[360, "ko"], [390, "ko"], [430, "en"], [1440, "ko"]]) {
    test(`file, preflight, loading, two top-five lists and rerun (${width}px ${language})`, async () => {
        let release;
        const {browser, page, calls, errors} = await open(width, language, {analyze: async route => {
            await new Promise(resolve => { release = resolve; });
            return route.fulfill({json: example()});
        }});
        try {
            assert.equal(await page.locator("#se-file").getAttribute("capture"), null);
            assert.match(await page.locator("#se-file").getAttribute("accept"), /xlsx/);
            await page.locator(".se-format-help summary").click();
            assert.match(await page.locator(".se-format-help").innerText(), /32/);
            assert.match(await page.locator(".se-format-help").innerText(), /20/);
            await page.locator(".se-format-help summary").click();
            await choose(page);
            assert.match(await page.locator("#se-file-check").innerText(), /2,400/);
            await page.locator("#se-run").click();
            await page.locator("#se-loading").waitFor({state: "visible"});
            await page.waitForFunction(() => !SimpleEditing.getLifecycleState().canClose);
            assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
            const panel = await page.locator(".se-loading-panel").boundingBox();
            assert.ok(panel.y + panel.height < await page.evaluate(() => innerHeight));
            assert.equal(await page.locator(".se-loading-track[aria-valuenow]").count(),0);
            await page.emulateMedia({reducedMotion:"reduce"});
            assert.equal(await page.locator(".se-loading-track span").evaluate(el=>getComputedStyle(el).animationName),"none");
            await page.screenshot({path:path.join(root,`.runtime/key-rules-loading-${width}.png`),fullPage:true});
            assert.equal(calls.filter(x => x.endsWith("/analyze")).length, 1);
            await page.evaluate(() => document.querySelector("#se-run").click());
            release();
            await page.locator("#se-results").waitFor({state: "visible"});
            assert.equal(await page.locator('#se-results [role="tab"]').count(), 2);
            assert.equal(await page.locator("#se-rules-formula article").count(), 3);
            await page.locator("#se-more").click();
            assert.equal(await page.locator("#se-rules-formula article").count(), 5);
            await page.locator(".se-analysis-help summary").click();
            assert.match(await page.locator("#se-summary").innerText(), /10,000/);
            assert.match(await page.locator(".se-analysis-help").innerText(), language === "en" ? /Condition and formula rules both use mixed pattern discovery/ : /조건규칙·수식규칙 모두 혼합형 패턴/);
            await page.locator(".se-analysis-help summary").click();
            await page.locator("#se-tab-condition").click();
            assert.equal(await page.locator("#se-rules-condition article:visible").count(), 3);
            await page.locator("#se-tab-condition").press("Home");
            assert.equal(await page.locator("#se-tab-formula").getAttribute("aria-selected"), "true");
            assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
            await page.locator("#se-rerun").click();
            await page.locator("#se-loading").waitFor({state: "visible"});
            while (calls.filter(x => x.endsWith("/analyze")).length < 2) await new Promise(resolve => setTimeout(resolve, 20));
            release();
            await page.locator("#se-results").waitFor({state: "visible"});
            assert.equal(calls.filter(x => x.endsWith("/preflight")).length, 1);
            assert.deepEqual(errors, []);
        } finally { await browser.close(); }
    });
}

test("bad headers and too few rows are shown before analysis, and reselect recovers", async () => {
    let valid = false;
    const {browser, page, calls} = await open(390, "ko", {preflight: route => route.fulfill(valid
        ? {json: {status: "success", data: {sourceRows: 2400, columns: 8}}}
        : {status: 400, json: {detail: {code: "TOO_FEW_ROWS", message: "헤더 제외 31행입니다. 최소 32행이 필요합니다."}}})});
    try {
        await page.locator("#se-file").setInputFiles(sampleFile);
        await page.locator("#se-error").waitFor({state: "visible"});
        assert.match(await page.locator("#se-error").innerText(), /31.*32/);
        assert.ok(await page.locator("#se-run").isDisabled());
        assert.equal(calls.filter(x => x.endsWith("/analyze")).length, 0);
        valid = true;
        await page.locator("#se-file").setInputFiles({name: "valid.csv", mimeType: "text/csv", buffer: fs.readFileSync(sampleFile)});
        await page.waitForFunction(() => !document.querySelector("#se-run").disabled);
        assert.ok(await page.locator("#se-error").isHidden());
    } finally { await browser.close(); }
});

for (const language of ["ko", "en"]) {
    test(`more than 100 columns warns before execution and reports the same result scope (${language})`, async () => {
        let wide = true;
        const {browser, page, calls, errors} = await open(390, language, {
            preflight: route => route.fulfill({json:{status:"success",data:{sourceRows:2400, columns:wide ? 100 : 8, sourceColumns:wide ? 105 : 8, omittedColumns:wide ? 5 : 0, columnLimit:100}}}),
            analyze: route => {
                const response = example();
                Object.assign(response.data, {columns:100, sourceColumns:105, omittedColumns:5, columnLimit:100});
                return route.fulfill({json:response});
            }
        });
        try {
            await choose(page);
            const notice = await page.locator("#se-column-notice").innerText();
            for (const count of [105, 100, 5]) assert.ok(notice.includes(String(count)));
            assert.ok(await page.locator("#se-run").isEnabled());
            assert.ok(await page.locator("#se-error").isHidden());
            assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
            await page.screenshot({path:path.join(root, `.runtime/rule-discovery-columns-${language}.png`), fullPage:true});
            await page.locator("#se-run").click();
            await page.locator("#se-results").waitFor({state:"visible"});
            const resultNotice = await page.locator("#se-result-column-notice").innerText();
            for (const count of [105, 100, 5]) assert.ok(resultNotice.includes(String(count)));
            assert.equal(calls.filter(call => call.endsWith("/analyze")).length, 1);
            wide = false;
            await page.locator("#se-new").click();
            await choose(page);
            assert.ok(await page.locator("#se-column-notice").isHidden());
            assert.ok(await page.locator("#se-result-column-notice").isHidden());
            assert.deepEqual(errors, []);
        } finally { await browser.close(); }
    });
}

test("server session is required even when a file is selected", async () => {
    const {browser, page, calls} = await open(390, "ko", {loggedOut: true});
    try {
        await page.locator("#se-login").waitFor({state: "visible"});
        await page.locator("#se-file").setInputFiles(sampleFile);
        assert.ok(await page.locator("#se-run").isDisabled());
        assert.equal(calls.filter(x => /\/(preflight|analyze)$/.test(x)).length, 0);
    } finally { await browser.close(); }
});

test("no-rule results and server failure never display invented or stale rules", async () => {
    let fail = false;
    const {browser, page} = await open(390, "ko", {analyze: route => route.fulfill(fail
        ? {status: 503, json: {detail: "현재 분석 중입니다. 잠시 후 다시 실행해 주세요."}}
        : {json: {status: "success", data: {sourceRows: 40, sampleRows: 40, elapsedSeconds: 1, rules: {FORMULA: [], CONDITION: []}}}})});
    try {
        await choose(page); await page.locator("#se-run").click();
        await page.locator("#se-results").waitFor({state: "visible"});
        assert.equal(await page.locator(".se-rule-card").count(), 0);
        assert.match(await page.locator("#se-rules-formula").innerText(), /없어요/);
        fail = true; await page.locator("#se-rerun").click();
        await page.locator("#se-error").waitFor({state: "visible"});
        assert.ok(await page.locator("#se-results").isHidden());
    } finally { await browser.close(); }
});

test("file labels and formula text are rendered as text, with no script execution", async () => {
    const response = example(); response.data.rules.FORMULA[0].result = '<img src=x onerror="window.injected=true">';
    const {browser, page} = await open(360, "ko", {analyze: route => route.fulfill({json: response})});
    try {
        await choose(page); await page.locator("#se-run").click();
        await page.locator("#se-results").waitFor({state: "visible"});
        assert.equal(await page.locator(".se-rule-card img").count(), 0);
        assert.equal(await page.evaluate(() => Boolean(window.injected)), false);
    } finally { await browser.close(); }
});

test("one-click live example uses the real CSV and the same preflight and analysis requests", async () => {
    const {browser, page, calls, errors} = await open(1280);
    try {
        await page.locator("#se-session[data-state=connected]").waitFor();
        await page.locator("#se-sample-run").click();
        await page.locator("#se-results").waitFor({state:"visible"});
        assert.equal(calls.filter(x => x.endsWith("/preflight")).length, 1);
        assert.equal(calls.filter(x => x.endsWith("/analyze")).length, 1);
        assert.match(await page.locator("#se-result-file").textContent(), /데모_거래.csv/);
        await page.locator("#se-rules-formula .se-rule-open").first().click();
        await page.locator("#se-detail").waitFor({state:"visible"});
        assert.match(await page.locator("#se-detail-stats").innerText(), /3,200/);
        assert.deepEqual(errors, []);
    } finally { await browser.close(); }
});

test("visible demo refreshes the server session, preserves file errors, and clears revoked or changed-account results", async () => {
    let status = 200, userId = 7;
    const {browser, page, calls} = await open(1280, "ko", {session: route => route.fulfill({status, json:{user:{userId}, sessionTtlSeconds:3600}})});
    try {
        await page.locator("#se-session[data-state=connected]").waitFor();
        await page.clock.install();
        await page.evaluate(() => SimpleEditing.onShow());
        const initial = calls.filter(x => x.endsWith("/session")).length;
        await page.clock.fastForward(91000);
        await page.waitForFunction(() => document.querySelector("#se-session").dataset.state === "connected");
        assert.ok(calls.filter(x => x.endsWith("/session")).length > initial);
        await page.locator("#se-file").setInputFiles({name:"wrong.exe", mimeType:"application/octet-stream", buffer:Buffer.from("bad")});
        const message = await page.locator("#se-error").innerText();
        await page.evaluate(() => SimpleEditing.onShow());
        assert.equal(await page.locator("#se-error").innerText(), message);
        await choose(page); await page.locator("#se-run").click();
        await page.locator("#se-results").waitFor({state:"visible"});
        userId = 8; await page.evaluate(() => SimpleEditing.onShow());
        assert.equal(await page.locator(".se-rule-card").count(), 0);
        assert.ok(await page.locator("#se-run").isDisabled());
        await choose(page); await page.locator("#se-run").click();
        await page.locator("#se-results").waitFor({state:"visible"});
        status = 401; await page.evaluate(() => SimpleEditing.onShow());
        assert.equal(await page.locator("#se-session").getAttribute("data-state"), "expired");
        assert.equal(await page.locator(".se-rule-card").count(), 0);
        assert.ok(await page.locator("#se-run").isDisabled());
        assert.ok(await page.locator("#se-login").isVisible());
    } finally { await browser.close(); }
});

test("visual review with actual demo discovery output when available", async () => {
    const fixture = path.join(root, ".runtime/simple-demo-result.json");
    if (!fs.existsSync(fixture)) return;
    const actual = JSON.parse(fs.readFileSync(fixture, "utf8"));
    for (const width of [390, 1280, 1440]) {
        const {browser, page} = await open(width, "ko", {analyze: route => route.fulfill({json: actual})});
        try {
            await page.locator("#se-session[data-state=connected]").waitFor();
            await page.screenshot({path: path.join(root, `.runtime/demo-studio-input-${width}.png`), fullPage: true});
            await choose(page); await page.locator("#se-run").click();
            await page.locator("#se-results").waitFor({state: "visible"});
            await page.screenshot({path: path.join(root, `.runtime/demo-studio-result-${width}.png`), fullPage: true});
            await page.locator("#se-rules-formula .se-rule-open").first().click();
            await page.screenshot({path:path.join(root, `.runtime/discovery-formula-detail-${width}.png`),fullPage:true});
            await page.locator("#se-detail-tab-data").click();
            await page.screenshot({path:path.join(root, `.runtime/discovery-formula-data-${width}.png`),fullPage:true});
        } finally { await browser.close(); }
    }
});

for (const [width, language] of [[390,"ko"],[430,"en"],[1280,"ko"]]) {
    test(`compact summary drills into formula graph, linked row data and history (${width}px ${language})`, async () => {
        const {browser,page,errors} = await open(width, language);
        try {
            await choose(page); await page.locator("#se-run").click();
            await page.locator("#se-results").waitFor({state:"visible"});
            assert.equal(await page.locator("#se-rules-formula article").count(),3);
            assert.ok(await page.locator(".se-rule-equation").first().evaluate(el => parseFloat(getComputedStyle(el).fontSize) >= 18));
            await page.locator("#se-rules-formula .se-rule-open").first().click();
            await page.locator("#se-detail").waitFor({state:"visible"});
            assert.match(page.url(),/#rule-/);
            assert.equal(await page.locator("#se-chart .se-dot").count(),120);
            await page.locator("#se-chart svg").focus();
            await page.locator("#se-chart svg").press("Home");
            await page.locator("#se-chart svg").press("ArrowRight");
            assert.match(await page.locator("#se-row-inspector").innerText(),/101/);
            assert.equal(await page.evaluate(() => document.activeElement?.tagName.toLowerCase()),"svg");
            await page.locator("#se-chart .se-dot").last().click();
            assert.match(await page.locator("#se-row-inspector").innerText(),/219/);
            assert.match(await page.locator("#se-row-inspector").innerText(),/1300/);
            await page.locator("#se-detail-tab-data").click();
            assert.equal(await page.locator("#se-data-page").innerText(),"6 / 6");
            assert.match(await page.locator("#se-data-table tr.is-selected").innerText(),/219/);
            await page.locator("[data-row-filter=DIFFERENT]").click();
            assert.equal(await page.locator("#se-data-table tbody tr").count(),8);
            assert.ok(await page.locator("#se-row-inspector").isHidden());
            const downloaded = page.waitForEvent("download");
            await page.locator("#se-data-download").click();
            const download = await downloaded;
            const csv = fs.readFileSync(await download.path(),"utf8");
            assert.equal(csv.split("\r\n").length,9);
            assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
            await page.goBack();
            await page.locator("#se-results").waitFor({state:"visible"});
            assert.equal(await page.locator("#se-rules-formula article").count(),3);
            await page.goForward();
            await page.locator("#se-detail").waitFor({state:"visible"});
            await page.locator("#se-detail-back").click();
            await page.locator("#se-results").waitFor({state:"visible"});
            assert.deepEqual(errors,[]);
        } finally {await browser.close();}
    });
}

test("condition counts drill into differing rows and a selected row's source values",async () => {
    const {browser,page,errors} = await open(390);
    try {
        await choose(page); await page.locator("#se-run").click();
        await page.locator("#se-results").waitFor({state:"visible"});
        await page.locator("#se-tab-condition").click();
        await page.locator("#se-rules-condition .se-rule-open").first().click();
        await page.locator("[data-bar-filter=DIFFERENT]").click();
        assert.equal(await page.locator("#se-detail-tab-data").getAttribute("aria-selected"),"true");
        assert.equal(await page.locator("#se-data-table tbody tr").count(),8);
        await page.locator("#se-data-table tbody tr").first().click();
        assert.match(await page.locator("#se-row-inspector").innerText(),/VIP/);
        assert.match(await page.locator("#se-row-inspector").innerText(),/일반배송/);
        await page.locator("#se-data-table tbody tr").first().focus();
        await page.locator("#se-data-table tbody tr").first().press("Enter");
        assert.equal(await page.evaluate(() => document.activeElement?.dataset.rowId),"0");
        await page.locator("#se-detail-back").click();
        await page.locator("#se-results").waitFor({state:"visible"});
        assert.equal(await page.locator("#se-tab-condition").getAttribute("aria-selected"),"true");
        assert.deepEqual(errors,[]);
    } finally {await browser.close();}
});

test("the three highlights favor different column relationships while all five rules remain accessible",async () => {
    const response = example();
    response.data.rules.FORMULA[2].detail.inputs = [{key:"C004",label:"수량"}];
    response.data.rules.FORMULA[2].result = "두 번째 관계";
    response.data.rules.FORMULA[4].detail.inputs = [{key:"C005",label:"단가"}];
    response.data.rules.FORMULA[4].result = "세 번째 관계";
    const {browser,page} = await open(1280,"ko",{analyze:route => route.fulfill({json:response})});
    try {
        await choose(page); await page.locator("#se-run").click();
        await page.locator("#se-results").waitFor({state:"visible"});
        const text = await page.locator("#se-rules-formula").innerText();
        assert.match(text,/두 번째 관계/); assert.match(text,/세 번째 관계/);
        await page.locator("#se-more").click();
        assert.equal(await page.locator("#se-rules-formula article").count(),5);
    } finally {await browser.close();}
});

test("detail labels stay text and CSV cells cannot become spreadsheet formulas",async () => {
    const response = example();
    response.data.rules.FORMULA[0].detail.inputs[0].label = '<img src=x onerror="window.injected=true">';
    response.data.rules.FORMULA[0].detail.rows[0].values.C001 = "=1+1";
    const {browser,page} = await open(1280,"ko",{analyze:route => route.fulfill({json:response})});
    try {
        await choose(page); await page.locator("#se-run").click();
        await page.locator("#se-rules-formula .se-rule-open").first().click();
        await page.locator("#se-detail-tab-data").click();
        assert.equal(await page.locator("#se-detail img").count(),0);
        assert.equal(await page.evaluate(() => Boolean(window.injected)),false);
        const downloaded = page.waitForEvent("download"); await page.locator("#se-data-download").click();
        const csv = fs.readFileSync(await (await downloaded).path(),"utf8");
        assert.ok(csv.includes("'=1+1"));
    } finally {await browser.close();}
});

test("a revoked session clears detailed charts, rows and history as well as the summary",async () => {
    let status = 200;
    const {browser,page} = await open(1280,"ko",{session:route => route.fulfill({status,json:{user:{userId:7},sessionTtlSeconds:3600}})});
    try {
        await choose(page); await page.locator("#se-run").click();
        await page.locator("#se-rules-formula .se-rule-open").first().click();
        status = 401; await page.evaluate(() => SimpleEditing.onShow());
        assert.ok(await page.locator("#se-detail").isHidden());
        assert.equal(await page.locator("#se-chart circle").count(),0);
        assert.equal(await page.locator("#se-data-table tr").count(),0);
        assert.equal(new URL(page.url()).hash,"");
    } finally {await browser.close();}
});

for (const [width, language] of [[390,"ko"],[430,"en"]]) {
    test(`sample violations remain separate from perfect selection validation (${language})`, async () => {
        const response = example();
        const rule = response.data.rules.FORMULA[0];
        rule.detail.stats.unscorable = 1;
        Object.assign(rule.detail.rows[0], {status:"UNSCORABLE", actual:null, residual:null});
        rule.detail.rows[0].values.C003 = "invalid";
        const {browser,page,errors} = await open(width,language,{analyze:route => route.fulfill({json:response})});
        try {
            await choose(page); await page.locator("#se-run").click();
            const summary = await page.locator("#se-rules-formula .se-rule-match").first().innerText();
            assert.match(summary,/8/); assert.match(summary,/3,200/); assert.doesNotMatch(summary,/100%/);
            await page.locator("#se-rules-formula .se-rule-open").first().click();
            const values = await page.locator("#se-detail-stats strong").allTextContents();
            assert.deepEqual(values,["8","3,200","3,192"]);
            assert.match(await page.locator("#se-detail-validation").textContent(),/100%.*800/);
            assert.ok(await page.locator("#se-detail-validation").isHidden());
            await page.locator("#se-detail-stats [data-filter=DIFFERENT]").click();
            assert.equal(await page.locator("#se-data-table tbody tr").count(),8);
            assert.match(await page.locator("#se-data-table").innerText(),/invalid/);
            assert.match(await page.locator("#se-data-scope").innerText(),/3,200/);
            const downloaded = page.waitForEvent("download"); await page.locator("#se-data-download").click();
            const download = await downloaded;
            assert.equal(download.suggestedFilename(),"Rule_Discovery_analyzed_sample.csv");
            const csv = fs.readFileSync(await download.path(),"utf8");
            assert.match(csv,/invalid/);
            assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
            assert.deepEqual(errors,[]);
        } finally {await browser.close();}
    });
}

test("legacy validation-only details are excluded from the violations-only list",async () => {
    const response=example(); response.data.rules.FORMULA[0].detail.cohort="SELECTION_VALIDATION";
    const {browser,page}=await open(390,"ko",{analyze:route=>route.fulfill({json:response})});
    try {
        await choose(page); await page.locator("#se-run").click();
        assert.equal(await page.locator("#se-rules-formula .se-rule-violations").first().innerText(),"위반 8");
        assert.equal(await page.locator("#se-rules-formula .se-rule-applied").first().innerText(),"3,200행 적용");
        assert.equal(await page.locator("#se-rules-formula").innerText().then(text => text.includes("미측정")),false);
    } finally {await browser.close();}
});

test("both families exclude clean rules before the five-card limit and explain an all-clean result", async () => {
    const response = example();
    response.data.discoveredCounts = {FORMULA: 7, CONDITION: 7};
    for (const kind of ["FORMULA", "CONDITION"]) {
        response.data.rules[kind].forEach((rule, i) => {
            rule.result = `${kind} ${i}`;
            if (i < 5) rule.detail.stats.different = 0;
        });
    }
    const {browser, page, errors} = await open(390, "ko", {analyze: route => route.fulfill({json:response})});
    try {
        await choose(page); await page.locator("#se-run").click();
        await page.locator("#se-results").waitFor({state:"visible"});
        for (const kind of ["formula", "condition"]) {
            await page.locator(`#se-tab-${kind}`).click();
            assert.equal(await page.locator(`#se-rules-${kind} article`).count(), 2);
            assert.match(await page.locator(`#se-rules-${kind}`).innerText(), /[56]/);
            assert.doesNotMatch(await page.locator(`#se-rules-${kind}`).innerText(), /위반 0 /);
        }
        Object.values(response.data.rules).flat().forEach(rule => {rule.detail.stats.different = 0;});
        await page.locator("#se-rerun").click();
        await page.locator("#se-rules-formula .se-empty").waitFor();
        assert.match(await page.locator("#se-rules-formula").innerText(), /위반이 확인된 규칙이 없어요/);
        await page.locator("#se-tab-condition").click();
        assert.match(await page.locator("#se-rules-condition").innerText(), /분석한 표본/);
        assert.deepEqual(errors, []);
    } finally {await browser.close();}
});


for (const width of [360, 1280]) {
    test(`long formulas fit the compact popup overview and keep full details (${width}px)`, async () => {
        const response = example();
        const formulas = [
            "1인당가처분소득_만원 ≈ (균등화가처분소득_만원 / sqrt(가구원수))",
            "가처분소득_만원 ≈ (월총소득_만원 - 세금사회보험료_만원)",
            "월근로소득_만원 ≈ (((월총소득_만원 - 월사업소득_만원) - 월이전소득_만원) - 월기타소득_만원)"
        ];
        response.data.rules.FORMULA.forEach((rule,i) => {
            rule.result = formulas[i % formulas.length];
            rule.condition = "(균등화가처분소득_만원 값 있음 그리고 가구원수 값 있음 그리고 가구원수 > 0)";
        });
        const {browser,page,errors} = await open(width,"ko",{analyze:route=>route.fulfill({json:response})});
        try {
            if (width > 700) await page.setViewportSize({width,height:760});
            await choose(page); await page.locator("#se-run").click();
            await page.locator("#se-results").waitFor({state:"visible"});
            const cards = page.locator("#se-rules-formula article");
            assert.equal(await cards.count(),3);
            const third = await cards.nth(2).boundingBox();
            assert.ok(third.y + third.height < await page.evaluate(() => innerHeight), "all three highlights must fit the viewport");
            const actions = await page.locator(".se-result-actions").boundingBox();
            assert.ok(actions.y + actions.height < await page.evaluate(() => innerHeight), "overview actions must stay visible");
            assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
            await page.screenshot({path:path.join(root,`.runtime/key-rules-compact-${width}.png`),fullPage:true});
            await cards.nth(2).locator(".se-rule-open").click();
            await page.screenshot({path:path.join(root,`.runtime/key-rules-detail-${width}.png`),fullPage:true});
            assert.equal(await page.locator("#se-detail-title").textContent(),formulas[2]);
            assert.equal(await page.locator("#se-detail-condition").textContent(),`적용 조건 · ${response.data.rules.FORMULA[2].condition}`);
            await page.locator("#se-detail-back").click();
            await page.locator("#se-results").waitFor({state:"visible"});
            await page.locator("#se-more").click();
            assert.equal(await cards.count(),5);
            assert.deepEqual(errors,[]);
        } finally {await browser.close();}
    });
}


function storedExample() {
    const response = example();
    response.data.detectionScope = "STORED_TARGET";
    response.data.history = {flowRunId:50,project:"Project",scenario:"Scenario",targetTable:"SOURCE_DATA"};
    for (const kind of ["FORMULA","CONDITION"]) {
        response.data.rules[kind] = response.data.rules[kind].slice(0,5);
        response.data.rules[kind].forEach((rule,i) => {
            rule.id = `${kind}${i}`; rule.storedRuleKey = rule.id;
            rule.detail.cohort = "STORED_DETECTION"; rule.detail.stats = {different:54,applied:1500,matched:1446};
            rule.detail.loaded = false; rule.detail.rows = []; rule.validationConfidence = null;
        });
    }
    return response;
}
for (const [width,language] of [[390,"ko"],[1280,"en"]]) {
    test(`Quick past runs open as stored key rules without analysis (${width}px ${language})`, async () => {
        const response = storedExample(), requests = [];
        const {browser,page,calls,errors} = await open(width,language,{
            session:route=>route.fulfill({json:{user:{userId:7},targetConnectionId:21,sessionTtlSeconds:3600}}),
            history:(route,url)=>{
                requests.push({path:url.pathname,query:Object.fromEntries(url.searchParams),method:route.request().method(),target:route.request().headers()["x-target-connection-id"]});
                if (url.pathname === "/api/M00002/history") {
                    const second = url.searchParams.get("page") === "2";
                    return route.fulfill({json:{status:"success",total:21,data:Array.from({length:second?1:20},(_,i)=>({FLOW_RUN_ID:second?70:50+i,STATUS:"SUCCESS",STARTED_AT:"2026-10-26T10:00:00",PROJECT_NAME:i?"Project":"<img src=x>",SCENARIO_NAME:"Scenario",OWNER_NAME:"APP",TABLE_NAME:"SOURCE_DATA"}))}});
                }
                if (!url.searchParams.has("ruleKey")) return route.fulfill({json:response});
                const rule = JSON.parse(JSON.stringify(response.data.rules.FORMULA[0]));
                rule.detail.loaded = true; rule.detail.inputs = [];
                rule.detail.rows = [{id:0,sourceRow:"CASE-001",status:"DIFFERENT",expected:100,actual:103,residual:3,values:{C003:"103"}},{id:1,sourceRow:"CASE-002",status:"UNSCORABLE",expected:100,actual:null,residual:null,values:{C003:"bad"}}];
                return route.fulfill({json:{status:"success",data:rule}});
            }
        });
        try {
            await page.waitForFunction(()=>!document.querySelector("#se-history-open").disabled);
            await page.evaluate(()=>sessionStorage.setItem("targetConnectionId","999"));
            await page.locator("#se-history-open").click();
            await page.locator(".se-history-row").first().waitFor();
            assert.equal(await page.locator(".se-history-row").count(),20);
            assert.equal(await page.locator("#se-history-list img").count(),0);
            await page.locator("#se-history-more").click();
            await page.waitForFunction(()=>document.querySelectorAll(".se-history-row").length === 21);
            await page.screenshot({path:path.join(root,`.runtime/key-rules-history-${width}.png`),fullPage:true});
            await page.locator(".se-history-row").first().click();
            await page.locator("#se-results").waitFor({state:"visible"});
            await page.waitForFunction(()=>!document.querySelector("#se-history-dialog").open);
            assert.equal(await page.locator("#se-rules-formula article").count(),3);
            assert.ok(await page.locator("#se-rerun").isHidden());
            assert.ok(await page.locator("#se-history-other").isVisible());
            await page.locator(".se-analysis-help summary").click();
            assert.match(await page.locator("#se-summary").innerText(),/#50/);
            assert.doesNotMatch(await page.locator("#se-summary").innerText(),/10,000/);
            await page.locator(".se-analysis-help summary").click();
            assert.equal(requests.filter(r=>r.query.ruleKey).length,0);
            await page.locator("#se-rules-formula .se-rule-open").first().click();
            await page.locator("#se-detail").waitFor({state:"visible"});
            assert.deepEqual(await page.locator("#se-detail-stats strong").allTextContents(),["54","1,500","1,446"]);
            await page.locator(".se-detail .se-help summary").click();
            assert.match(await page.locator("#se-detail-help").innerText(),language === "ko" ? /저장된 탐지/ : /Stored detection/);
            await page.locator("#se-detail-tab-data").click();
            assert.match(await page.locator("#se-data-table").innerText(),/CASE-001/);
            assert.match(await page.locator("#se-data-scope").innerText(),language === "ko" ? /저장된 위반 예시 2개.*54/ : /2 saved examples.*54/);
            await page.locator("#se-data-table tbody tr").first().click();
            assert.match(await page.locator("#se-row-inspector").innerText(),/CASE-001/);
            assert.doesNotMatch(await page.locator("#se-row-inspector").innerText(),/NaN/);
            await page.locator("#se-detail-back").click();
            await page.locator("#se-rules-formula .se-rule-open").first().click();
            assert.equal(requests.filter(r=>r.query.ruleKey).length,1);
            assert.ok(requests.every(r=>r.method === "GET" && r.target === "21"));
            assert.ok(!calls.some(call=>call.endsWith("/analyze") || call.endsWith("/preflight")));
            assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth));
            assert.deepEqual(errors,[]);
        } finally {await browser.close();}
    });
}

test("stored history failures retry and Target DB change discards a delayed result", async () => {
    let target=21,fail=true,release;
    const {browser,page,errors} = await open(390,"ko",{
        session:route=>route.fulfill({json:{user:{userId:7},targetConnectionId:target}}),
        history:async(route,url)=>{
            if (url.pathname === "/api/M00002/history") return route.fulfill(fail?{status:503,json:{detail:"History unavailable"}}:{json:{status:"success",total:1,data:[{FLOW_RUN_ID:50,PROJECT_NAME:"Project",STATUS:"FAILED"}]}});
            await new Promise(resolve=>{release=resolve;});
            try {await route.fulfill({json:storedExample()});}catch(_){}
        }
    });
    try {
        await page.waitForFunction(()=>!document.querySelector("#se-history-open").disabled);
        await page.locator("#se-history-open").click();
        await page.waitForFunction(()=>document.querySelector("#se-history-count").textContent.includes("History unavailable"));
        fail=false; await page.locator("#se-history-refresh").click(); await page.locator(".se-history-row").waitFor();
        await page.locator(".se-history-row").click();
        while (!release) await page.waitForTimeout(10);
        target=22; await page.evaluate(()=>SimpleEditing.onShow()); release();
        await page.locator("#se-input-panel").waitFor({state:"visible"});
        assert.equal(await page.locator("#se-results").isVisible(),false);
        assert.equal(await page.locator("#se-rules-formula article").count(),0);
        assert.equal(await page.locator("#se-history-dialog").evaluate(el=>el.open),false);
        assert.deepEqual(errors,[]);
    } finally {await browser.close();}
});
