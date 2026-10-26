(function () {
    "use strict";
    window.KeyRuleHistory = function ({t, context, onSelect, onExpired, onConflict}) {
        const $ = id => document.getElementById(id), dialog = $("se-history-dialog");
        let rows = [], page = 0, total = 0, loading = false, message = "", abort = null, generation = 0;
        const identity = () => {const ctx = context(); return `${ctx.user}:${ctx.target}`;};
        const el = (tag, value, css = "") => {const node = document.createElement(tag); node.textContent = value; node.className = css; return node;};
        function render() {
            $("se-history-close").setAttribute("aria-label",t("historyClose"));
            $("se-history-count").textContent = loading ? t("historyLoading") : message || t("historyCount").replace("{count}", total);
            $("se-history-refresh").disabled = loading;
            $("se-history-more").hidden = loading || rows.length >= total;
            const list = $("se-history-list"); list.replaceChildren();
            for (const row of rows) {
                const button = el("button", "", "se-history-row"); button.type = "button"; button.disabled = loading;
                const main = el("span", "", "se-history-main");
                main.append(el("small", `#${row.FLOW_RUN_ID} · ${String(row.STARTED_AT || row.CREATED_AT || "").replace("T", " ").slice(0,19)}`),
                    el("strong", [row.PROJECT_NAME || row.PROJECT_CODE, row.SCENARIO_NAME || row.SCENARIO_CODE].filter(Boolean).join(" · ")),
                    el("span", [row.OWNER_NAME,row.TABLE_NAME].filter(Boolean).join(".")));
                const status = String(row.STATUS || "").toUpperCase();
                const meta = el("span", "", "se-history-meta");
                meta.append(el("span", t(["SUCCESS","COMPLETED"].includes(status) ? "historySuccess" : ["FAILED","ERROR"].includes(status) ? "historyFailed" : ["RUNNING","QUEUED"].includes(status) ? "historyRunning" : status === "PAUSED" ? "historyPaused" : ["STOPPED","CANCELLED"].includes(status) ? "historyStopped" : "historyOther")), el("span", t("historyOpen")));
                button.append(main,meta);
                button.addEventListener("click", async () => {
                    if (loading) return;
                    loading = true; message = ""; const ticket = ++generation, owner = identity(); render();
                    try {await onSelect(Number(row.FLOW_RUN_ID)); if (ticket === generation && owner === identity()) dialog.close();}
                    catch (error) {if (ticket === generation && error.name !== "AbortError") message = error.message;}
                    finally {if (ticket === generation) {loading = false; render();}}
                });
                list.append(button);
            }
            if (!rows.length && !loading && !message) list.append(el("p",t("historyEmpty"),"se-muted"));
        }
        async function load(reset) {
            const ctx = context(); if (loading || !ctx.target) return;
            if (reset) {rows = []; page = 0; total = 0;}
            loading = true; message = ""; const ticket = ++generation, owner = identity();
            abort?.abort(); abort = new AbortController(); render();
            try {
                const response = await fetch(`/api/M00002/history?page=${page + 1}&pageSize=20`, {credentials:"include",cache:"no-store",headers:{"X-Target-Connection-Id":String(ctx.target)},signal:abort.signal});
                if (ticket !== generation || owner !== identity()) return;
                if ([401,403].includes(response.status)) {onExpired(); return;}
                if (response.status === 409) {onConflict(); return;}
                const payload = await response.json();
                if (ticket !== generation || owner !== identity()) return;
                if (!response.ok || payload.status !== "success" || !Array.isArray(payload.data)) throw new Error(typeof payload.detail === "string" ? payload.detail : t("historyError"));
                rows.push(...payload.data); page++; total = Number(payload.total || 0);
            } catch (error) {if (ticket === generation && error.name !== "AbortError") message = error.message || t("historyError");}
            finally {if (ticket === generation) {loading = false; render();}}
        }
        $("se-history-open").addEventListener("click", () => {dialog.showModal(); load(true);});
        $("se-history-close").addEventListener("click", () => dialog.close());
        $("se-history-refresh").addEventListener("click", () => load(true));
        $("se-history-more").addEventListener("click", () => load(false));
        return {
            open() {dialog.showModal(); load(true);},
            refresh() {if (dialog.open) render();},
            setEnabled(value) {$("se-history-open").disabled = !value;},
            reset() {++generation; abort?.abort(); loading=false; rows=[]; page=0; total=0; message=""; if (dialog.open) dialog.close();}
        };
    };
})();
