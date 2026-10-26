const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "../..");
const origin = "http://embedded-workspace.test";

async function openShell(width = 1440, language = "ko", completed = false, simple = false, realPopup = false) {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width, height: 980 } });
    const calls = [], errors = [];
    const serverSession = { userId: 7, targetConnectionId: 1 };
    page.on("pageerror", (error) => errors.push(error.message));
    const context = page.context();
    if (realPopup) await context.addCookies([{name: "init_session_v2", value: "verified-demo-fixture", domain: "embedded-workspace.test", path: "/", httpOnly: true, sameSite: "Lax"}]);
    await context.addInitScript(({ language, completed, realPopup }) => {
        if (!sessionStorage.getItem("workspaceFixture")) {
            sessionStorage.setItem("initLoginUser", JSON.stringify({ userId: 7, userName: "Review User", roleCode: "ADMIN" }));
            sessionStorage.setItem("initLanguageCode", language);
            sessionStorage.setItem("targetConnectionId", "1");
            sessionStorage.setItem("targetConnectionName", "Review Target DB");
            sessionStorage.setItem("initLoginExpiresAt", String(Date.now() + 3600000));
            sessionStorage.setItem("workspaceFixture", "1");
            sessionStorage.setItem("init.quick-edit.pipeline.v1", JSON.stringify({
                version: 1, sessionUserId: "7", processType: "UNIFIED", status: completed ? "success" : "idle", workspaceMode: "new",
                targetContextId: 1, ...(completed ? { projectId: 10, scenarioId: 20, flowId: 40, flowRunId: 50,
                    lastRunStatus: "SUCCESS", tableOwner: "REVIEW_OWNER", tableName: "INITUP$REVIEW", scenarioTableId: 30,
                    currentStep: 7, completedSteps: [0, 1, 2, 3, 4, 5, 6, 7] } : {})
            }));
        }
        window.popupCalls = [];
        if (!realPopup) window.open = (...args) => { window.popupCalls.push(args); return null; };
    }, { language, completed, realPopup });
    await context.route("**/*", async (route) => {
        const url = new URL(route.request().url());
        if (url.origin !== origin) return route.fulfill({ status: 404, body: "" });
        if (url.pathname.startsWith("/api/")) {
            const headers = await route.request().allHeaders();
            calls.push({ path: url.pathname, method: route.request().method(), cookie: headers.cookie });
            if (realPopup && url.pathname.startsWith("/api/M00002/") && !headers.cookie?.includes("init_session_v2=verified-demo-fixture")) return route.fulfill({status:401,json:{detail:"Login session is required."}});
            let data = { status: "success", data: [] };
            if (url.pathname.endsWith("/session/me") || url.pathname === "/api/M00002/session") data = { status: "success", targetConnectionId: serverSession.targetConnectionId,
                connection: { connectionName: serverSession.targetConnectionId === 1 ? "Review Target DB" : "Changed Target DB" },
                user: { userId: serverSession.userId, userName: "Review User", roleCode: "ADMIN" }, sessionTtlSeconds: 3600 };
            if (url.pathname.endsWith("/snapshot")) data = { status: "success", data: { run: { STATUS: "SUCCESS" }, nodes: [] } };
            if (url.pathname.endsWith("/mixed-xai-results")) data = { status: "success", data: {
                summary: { algorithm: "MIXED_PATTERN_TREE", ruleCount: 0, integratedEditing: { processType: "UNIFIED" } },
                rules: [], violations: [], ruleSummary: { rules: [], total: 0, overview: { TOTAL_RULES: 0 } } } };
            if (url.pathname.endsWith("/editing-results")) data = { status: "success", data: {
                family: url.searchParams.get("family") || "CONDITION", total: 0, page: 1, pageSize: 20, rules: [],
                summary: { families: { CONDITION: { total: 0 }, FORMULA: { total: 0 } }, sourceCounts: [], historicalExplanationCount: 0 }, diagnostics: {} } };
            if (url.pathname === "/api/M00002/preflight") data = {status:"success",data:{sourceRows:2400,sampleRows:2400,columns:8}};
            if (url.pathname === "/api/M00002/analyze") data = {status:"success",data:{sourceRows:2400,sampleRows:2400,elapsedSeconds:1,rules:{FORMULA:[{id:"f1",kind:"FORMULA",result:"결제금액 ≈ 상품금액 - 할인금액",condition:"상품금액 값 있음",validationConfidence:1,validationRows:600,supportRows:1350}],CONDITION:[]}}};
            return route.fulfill({ json: data, headers: { "X-INIT-Session-TTL-Seconds": "3600" } });
        }
        // Other main pages are boundary fixtures; the shell, PageManager, menu,
        // translation engine, styles, M00001 and its Quick Editing child are real.
        if (url.pathname === "/pages/home.html" && !simple) return route.fulfill({ contentType: "text/html", body: '<div id="container-home"><h1>Main Home</h1></div>' });
        if (url.pathname === "/js/home.js") return route.fulfill({ contentType: "application/javascript", body: "window.home={init(){}};" });
        let local = url.pathname === "/" ? path.join(root, "frontend/index.html")
            : /^\/(quick-edit|simple-edit)\//.test(url.pathname) ? path.join(root, url.pathname.slice(1), url.pathname.endsWith("/") ? "index.html" : "")
                : path.join(root, "frontend", url.pathname);
        if (!local.startsWith(root + path.sep) || !fs.existsSync(local) || !fs.statSync(local).isFile()) return route.fulfill({ status: 404, body: "" });
        const mime = { ".html": "text/html", ".js": "application/javascript", ".css": "text/css", ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml", ".woff2": "font/woff2" }[path.extname(local)] || "application/octet-stream";
        return route.fulfill({ contentType: mime, body: fs.readFileSync(local) });
    });
    try {
        await page.goto(origin + "/?page=home");
        await page.waitForFunction(() => window.PageManager?.readyPages.has("home"));
        if (simple) {
            if (realPopup) {
                const opened = page.waitForEvent("popup").catch(() => null);
                await page.locator(".simple-edit-launcher").click();
                assert.deepEqual(errors, [], "The demo launcher must not throw before opening its window");
                const popup = await opened;
                assert.ok(popup, "Demo popup should open from a direct user click");
                popup.on("pageerror", error => errors.push(error.message));
                await popup.locator("#se-session[data-state=connected]").waitFor({timeout:8000}).catch(async error => {
                    throw new Error(`${error.message}; popup=${popup.url()}; state=${await popup.locator("#se-session").textContent().catch(() => "missing")}; errors=${JSON.stringify(errors)}; requests=${JSON.stringify(calls.map(call => ({path:call.path,cookie:Boolean(call.cookie)})))}`);
                });
                return {browser, page, popup, calls, errors, serverSession};
            }
            await page.evaluate(() => openSimpleEditWindow());
            await page.waitForFunction(() => window.PageManager?.readyPages.has("M00002"));
            await page.waitForFunction(() => document.querySelector("#simpleEditFrame-M00002")?.contentWindow?.SimpleEditing);
            const frame = page.frames().find(item => item.url().includes("/simple-edit/"));
            return {browser, page, frame, calls, errors, serverSession};
        }
        await page.evaluate(() => document.querySelector('#mainNav [data-page="M00001"]').click());
        await page.waitForFunction(() => window.PageManager?.readyPages.has("M00001"));
        await page.waitForFunction(() => document.querySelector("#quickEditFrame-M00001")?.contentWindow?.location.pathname === "/quick-edit/");
        const frame = page.frames().find((item) => item.url().includes("/quick-edit/?embedded=1"));
        assert.ok(frame, "Quick Editing iframe must be mounted in the main shell");
        await frame.waitForFunction(() => window.QuickEditWorkspace && document.querySelector("#sessionStatus")?.dataset.state === "connected");
        return { browser, page, frame, calls, errors, serverSession };
    } catch (error) {
        await browser.close();
        throw error;
    }
}

for (const language of ["ko", "en"]) {
    test(`demo popup shares the HttpOnly server cookie, refreshes main TTL and reuses the result (${language})`, async () => {
        const {browser, page, popup, calls, errors} = await openShell(1440, language, false, true, true);
        try {
            const url = new URL(popup.url());
            assert.equal(url.pathname, "/simple-edit/");
            assert.deepEqual([...url.searchParams.keys()].sort(), ["lang", "v"]);
            assert.equal(await popup.locator("html").getAttribute("lang"), language);
            assert.equal(await popup.evaluate(() => document.cookie.includes("init_session_v2")), false);
            await popup.evaluate(() => sessionStorage.removeItem("initLoginUser"));
            await page.evaluate(() => sessionStorage.setItem("initLoginExpiresAt", String(Date.now() + 60000)));
            await popup.evaluate(() => SimpleEditing.onShow());
            assert.ok(await page.evaluate(() => Number(sessionStorage.getItem("initLoginExpiresAt")) - Date.now() > 3500000));
            await popup.locator("#se-sample-run").click();
            await popup.locator("#se-results").waitFor({state:"visible"});
            assert.ok(calls.filter(call => /\/M00002\/(session|preflight|analyze)$/.test(call.path)).every(call => call.cookie.includes("init_session_v2=verified-demo-fixture")));
            await popup.evaluate(() => { window.popupSentinel = "keep result"; });
            await page.locator(".simple-edit-launcher").click();
            await page.locator(".simple-edit-launcher").click();
            assert.equal(page.context().pages().length, 2);
            assert.equal(await popup.evaluate(() => popupSentinel), "keep result");
            assert.ok(await popup.locator("#se-results").isVisible());
            assert.equal(await page.locator("#simpleEditFrame-M00002").count(), 0);
            if (await popup.locator("#se-fullscreen").isVisible()) {
                await popup.locator("#se-fullscreen").click();
                await popup.waitForFunction(() => Boolean(document.fullscreenElement));
                await popup.locator("#se-fullscreen").click();
                await popup.waitForFunction(() => !document.fullscreenElement);
            }
            await popup.close();
            const opened = page.waitForEvent("popup");
            await page.locator(".simple-edit-launcher").click();
            const reopened = await opened;
            await reopened.locator("#se-session[data-state=connected]").waitFor();
            await reopened.locator("#se-sample-run").click();
            await reopened.locator("#se-results").waitFor({state:"visible"});
            await page.context().clearCookies();
            await reopened.evaluate(() => SimpleEditing.onShow());
            assert.equal(await reopened.locator("#se-session").getAttribute("data-state"), "expired");
            assert.equal(await reopened.locator(".se-rule-card").count(), 0);
            assert.ok(await reopened.locator("#se-run").isDisabled());
            assert.deepEqual(errors, []);
        } finally { await browser.close(); }
    });
}

for (const width of [390, 1440]) {
    test(`Key Rules stays off the menu and opens from its icon (${width}px)`, async () => {
        const {browser, page, frame, errors} = await openShell(width, "ko", false, true);
        try {
            assert.equal(await page.locator('#mainNav [data-page="M00002"]').count(), 0);
            assert.equal(await page.evaluate(() => PageManager.isPageAllowed("M00002")), true);
            const simple = page.locator(".simple-edit-launcher"), quick = page.locator(".quick-edit-launcher");
            assert.equal(await page.locator(".simple-edit-launcher-label").count(), 0);
            assert.equal((await simple.textContent()).trim(), "ƒ");
            assert.match(await simple.getAttribute("title"), /^핵심 규칙 찾기\n같은 혼합형 분석/);
            assert.match(await quick.getAttribute("title"), /^규칙 분석·데이터 편집\n/);
            assert.equal(await simple.getAttribute("aria-label"), "핵심 규칙 찾기");
            assert.equal(await quick.getAttribute("aria-label"), "규칙 분석·데이터 편집");
            if (!await simple.isVisible()) await page.locator("#mobileTopToolbarToggle").click();
            const simpleBox = await simple.boundingBox(), quickBox = await quick.boundingBox();
            assert.ok(Math.abs(simpleBox.width - quickBox.width) < 1);
            assert.ok(Math.abs(simpleBox.height - quickBox.height) < 1);
            assert.ok(simpleBox.width >= 38 && simpleBox.width <= 40);
            await page.evaluate(() => I18nManager.applyLanguage("en"));
            assert.equal(await simple.getAttribute("aria-label"), "Find key rules");
            assert.match(await quick.getAttribute("title"), /^Analyze rules and edit data/);
            assert.equal((await simple.textContent()).trim(), "ƒ");
            await page.evaluate(() => I18nManager.applyLanguage("ko"));
            assert.equal(await simple.getAttribute("aria-label"), "핵심 규칙 찾기");
            assert.equal(await quick.getAttribute("aria-label"), "규칙 분석·데이터 편집");
            assert.match(await frame.title(), /핵심 규칙 찾기/);
            assert.equal(await page.locator('#mainNav [data-page="M00001"]').count(), 1);
            const box = await page.locator("#simpleEditFrame-M00002").boundingBox();
            assert.ok(box.width > 280 && box.height >= 540);
            assert.ok(box.x >= 0 && box.x + box.width <= width + 1);
            assert.ok(await frame.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
            await page.evaluate(() => PageManager.load("home", "Home"));
            assert.equal(await page.locator(".home-simple-edit").count(), 0);
            assert.ok(await page.locator(".home-hero-panel").isVisible());
            await page.screenshot({path: path.join(root, `.runtime/rule-discovery-home-${width}.png`)});
            await page.evaluate(() => openSimpleEditWindow());
            assert.equal(await page.locator("#simpleEditFrame-M00002").count(), 1);
            assert.equal(await page.evaluate(() => popupCalls.length), 2);
            assert.deepEqual(errors, []);
        } finally { await browser.close(); }
    });
}

test("main menu and header share a cached Quick Editing page with close/refresh/Target DB guards", async () => {
    const { browser, page, frame, calls, errors } = await openShell();
    try {
        assert.deepEqual(await page.evaluate(() => MENU_CONFIG.slice(0, 3).map((item) => item.page)), ["home", "M00002", "M00001"]);
        assert.equal(await page.locator('#mainNav [data-page="M00001"]').innerText(), "퀵 에디팅");
        assert.equal(await page.locator("#quickEditFrame-M00001").getAttribute("title"), "퀵 에디팅");
        await frame.evaluate(() => { window.cacheSentinel = "same execution"; });
        await page.evaluate(async () => { await PageManager.load("home", "Home"); await openQuickEditWindow(); });
        assert.equal(await frame.evaluate(() => window.cacheSentinel), "same execution");
        assert.equal(await page.locator("#quickEditFrame-M00001").count(), 1);
        assert.equal(await page.evaluate(() => window.popupCalls.length), 0);
        await page.evaluate(() => {
            window.workspaceWarnings = [];
            CommonMessage.warning = (message) => workspaceWarnings.push(message);
            CommonMessage.confirm = async () => true;
        });
        for (const state of [{ busy: true, dirty: false }, { busy: false, dirty: true }]) {
            await frame.evaluate((state) => {
                window.originalLifecycle ||= window.QuickEditWorkspace;
                window.QuickEditWorkspace = { getLifecycleState: () => ({ ...state, canClose: false, message: "Work remains" }), canClose: () => false };
            }, state);
            await page.evaluate(async () => {
                await PageManager.load("M00001", "Quick Editing", true);
                await handlePageClose();
                await handleLogout();
                document.querySelector("#targetDbChangeList").innerHTML = '<input name="targetDbChangeConnectionId" value="2" type="radio" checked>';
                await applyTargetDbChange();
            });
            assert.equal(await frame.evaluate(() => window.cacheSentinel), "same execution");
            assert.equal(await page.evaluate(() => sessionStorage.getItem("targetConnectionId")), "1");
        }
        assert.equal(await page.evaluate(() => workspaceWarnings.length), 8);
        assert.equal(calls.filter((call) => /\/session\/(cleanup|target)$|\/logout$/.test(call.path)).length, 0);
        await frame.evaluate(() => { window.QuickEditWorkspace = window.originalLifecycle; });
        await page.evaluate(() => handlePageClose());
        await page.waitForFunction(() => !document.querySelector("#quickEditFrame-M00001"));
        assert.equal(await page.evaluate(() => PageManager.activePageCode), "home");
        assert.deepEqual(errors, []);
    } finally { await browser.close(); }
});

for (const [width, language] of [[1440, "ko"], [430, "en"]]) {
    test(`embedded Quick Editing fits the actual shell (${width}px ${language})`, async () => {
        const { browser, page, frame, errors } = await openShell(width, language);
        try {
            const box = await page.locator("#quickEditFrame-M00001").boundingBox();
            assert.ok(box.width > 280 && box.height >= 540);
            assert.ok(box.y + box.height >= 900, "Workspace should fill the available viewport height on desktop and mobile");
            assert.ok(box.x >= 0 && box.x + box.width <= width + 1);
            assert.equal(await frame.evaluate(() => document.body.classList.contains("qe-embedded")), true);
            assert.ok(await frame.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth));
            fs.mkdirSync(path.join(root, "test-results"), { recursive: true });
            await page.screenshot({ path: path.join(root, `test-results/quick-main-workspace-${language}-${width}.png`), fullPage: true });
            assert.deepEqual(errors, []);
        } finally { await browser.close(); }
    });
}

test("embedded detailed analysis activates the parent page and preserves the Quick Editing iframe", async () => {
    const { browser, page, frame } = await openShell(1440, "ko", true);
    try {
        await page.evaluate(() => {
            window.detailHandoff = {};
            const originalSet = Storage.prototype.setItem;
            Storage.prototype.setItem = function(key, value) {
                if (key.startsWith("M04002:")) window.detailHandoff[key] = String(value);
                return originalSet.call(this, key, value);
            };
        });
        await frame.locator("#qeOpenDetailedAnalysis").click();
        await page.waitForFunction(() => PageManager.activePageCode === "M04002");
        assert.equal(await page.evaluate(() => window.detailHandoff["M04002:selectedRunId"]), "50");
        assert.equal(await page.locator("#quickEditFrame-M00001").count(), 1);
        assert.equal(await page.evaluate(() => window.popupCalls.length), 0);
    } finally { await browser.close(); }
});

test("expired server session clears the cached Quick Editing page and saved state even when its task is busy", async () => {
    const { browser, page, frame, calls } = await openShell();
    try {
        await frame.evaluate(() => {
            window.QuickEditWorkspace = { getLifecycleState: () => ({ busy: true, canClose: false }), canClose: () => false };
        });
        await page.evaluate(async () => {
            window.alert = () => {};
            sessionStorage.setItem("init.quick-edit.context-notice.v1", "Old connection");
            await PageManager.handleSessionExpired();
        });
        assert.equal(await page.locator("#quickEditFrame-M00001").count(), 0);
        assert.equal(await page.evaluate(() => sessionStorage.getItem("init.quick-edit.pipeline.v1")), null);
        assert.equal(await page.evaluate(() => sessionStorage.getItem("init.quick-edit.context-notice.v1")), null);
        assert.equal(await page.evaluate(() => sessionStorage.getItem("initLoginUser")), null);
        assert.equal(await page.evaluate(() => PageManager.activePageCode), "login");
        assert.ok(calls.some((call) => /\/M91001\/logout$/.test(call.path)));
    } finally { await browser.close(); }
});

test("cached Quick Editing applies the main language when shown again without reloading its document", async () => {
    const { browser, page, frame, calls, errors } = await openShell(1440, "ko", true);
    try {
        await frame.waitForFunction(() => document.querySelector(".editing-result-view")?.getAttribute("aria-busy") === "false");
        await frame.evaluate(() => { window.cacheSentinel = "unchanged draft"; });
        const apiCount = calls.length;
        for (const [language, labels] of [["en", ["Condition rules (IF–THEN)", "Formula rules"]], ["ko", ["조건규칙 (IF–THEN)", "수식규칙"]]]) {
            await page.evaluate(async (language) => {
                await PageManager.load("home", "Home");
                await I18nManager.applyLanguage(language);
                await openQuickEditWindow();
            }, language);
            assert.equal(await frame.evaluate(() => window.cacheSentinel), "unchanged draft");
            assert.deepEqual(await frame.locator("[data-editing-family] strong").allTextContents(), labels);
            assert.equal(await frame.locator("html").getAttribute("lang"), language);
        }
        assert.equal(calls.length, apiCount, "Revisiting the cached page must not restart API work");
        assert.deepEqual(errors, []);
    } finally { await browser.close(); }
});

test("external Target DB recovery respects other-page guards and retries by replacing the entire old workspace", async () => {
    const { browser, page, frame, calls, errors, serverSession } = await openShell();
    try {
        await page.evaluate(() => {
            window.oldPageDestroyed = 0;
            window.home.beforeClose = () => false;
            window.home.destroy = () => { window.oldPageDestroyed += 1; };
        });
        await frame.evaluate(() => { window.cacheSentinel = "old DB context"; });
        serverSession.targetConnectionId = 2;
        await frame.evaluate(() => QuickEditWorkspace.onContextLoss({ status: 409 }));
        await frame.waitForFunction(() => document.querySelector("#qeContextRecoveryMessage").textContent.includes("다른 탭"));
        assert.equal(await frame.evaluate(() => window.cacheSentinel), "old DB context");
        assert.equal(await page.evaluate(() => sessionStorage.getItem("targetConnectionId")), "1");
        assert.equal(await page.evaluate(() => window.oldPageDestroyed), 0);
        assert.equal(await frame.locator("#qeContextRecoveryButton").isEnabled(), true);
        await page.evaluate(() => { window.home.beforeClose = () => true; });
        await frame.locator("#qeContextRecoveryButton").click();
        await page.waitForFunction(() => sessionStorage.getItem("targetConnectionId") === "2" && window.PageManager.readyPages.has("M00001"));
        assert.equal(await page.evaluate(() => window.oldPageDestroyed), 1);
        assert.equal(await page.locator("#page-section-home").count(), 0);
        assert.equal(await page.locator("#currentTargetDbText").innerText(), "Changed Target DB");
        await page.waitForFunction(() => document.querySelector("#quickEditFrame-M00001")?.contentWindow?.QuickEditWorkspace);
        assert.equal(await page.evaluate(() => document.querySelector("#quickEditFrame-M00001").contentWindow.cacheSentinel), undefined);
        assert.equal(calls.filter((call) => /\/session\/(cleanup|target)$|\/logout$|\/(stop|cancel)$/.test(call.path)).length, 0);
        assert.deepEqual(errors, []);
    } finally { await browser.close(); }
});

test("a different verified server account discards the old cached workspace despite an old-page close guard", async () => {
    const { browser, page, frame, serverSession } = await openShell();
    try {
        await page.evaluate(() => { window.home.beforeClose = () => false; });
        serverSession.userId = 8;
        serverSession.targetConnectionId = 2;
        await frame.evaluate(() => QuickEditWorkspace.onContextLoss({ status: 409 }));
        await page.waitForFunction(() => JSON.parse(sessionStorage.getItem("initLoginUser") || "null")?.userId === 8 && window.PageManager.readyPages.has("M00001"));
        assert.equal(await page.locator("#page-section-home").count(), 0);
        assert.equal(await page.evaluate(() => sessionStorage.getItem("targetConnectionId")), "2");
        assert.notEqual(await page.evaluate(() => JSON.parse(sessionStorage.getItem("init.quick-edit.pipeline.v1") || "null")?.sessionUserId), "7");
    } finally { await browser.close(); }
});
