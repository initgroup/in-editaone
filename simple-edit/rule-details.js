(function () {
    "use strict";
    const $ = id => document.getElementById(id);
    const node = (tag, className, value) => {
        const el = document.createElement(tag); el.className = className;
        if (value != null) el.textContent = value;
        return el;
    };
    window.RuleDiscoveryDetails = function ({t, number, onBack}) {
        let rule = null, tab = "graph", filter = "ALL", page = 0, selected = null;
        const pageSize = 20;
        const rows = () => rule?.detail?.rows || [];
        const stored = () => rule?.detail?.cohort === "STORED_DETECTION";
        const filtered = () => rows().filter(row => filter === "ALL" || (filter === "MATCH" ? row.status === "MATCH" : row.status !== "MATCH"));
        const statusText = status => t(status === "MATCH" ? "match" : status === "UNSCORABLE" ? "unscorable" : "different");
        const metric = value => value == null ? "—" : Math.abs(value) >= 1e7 || (value !== 0 && Math.abs(value) < .0001) ? Number(value).toExponential(2) : number(value);
        const axisMetric = value => value !== 0 && Math.abs(value) < .001 ? Number(value).toExponential(1)
            : new Intl.NumberFormat(document.documentElement.lang === "en" ? "en-US" : "ko-KR", {notation:"compact", maximumFractionDigits:1}).format(value);
        const fill = (key, values) => Object.entries(values).reduce((text, [key, value]) => text.replace(`{${key}}`, number(value)), t(key));
        function renderStats() {
            const stats = rule.detail?.stats;
            const definitions = [
                {value: stats ? number(stats.different) : "—", label: t("different"), filter: "DIFFERENT"},
                {value: stats?.applied != null ? number(stats.applied) : "—", label: t("checkedRows"), filter: "ALL"},
                {value: stats?.matched != null ? number(stats.matched) : "—", label: t("match"), filter: "MATCH"}
            ];
            $("se-detail-stats").replaceChildren(...definitions.map(definition => {
                const button = node("button", "se-stat"); button.type = "button"; button.dataset.filter = definition.filter;
                button.append(node("strong", "", definition.value), node("span", "", definition.label));
                button.addEventListener("click", () => setFilter(definition.filter));
                return button;
            }));
        }
        function renderOverview() {
            $("se-detail-help").textContent = t(stored() ? "storedDetailHelp" : "detailHelp");
            $("se-detail-title").textContent = rule.result;
            $("se-detail-condition").textContent = `${t("applies")} · ${rule.condition}`;
            $("se-detail-tolerance").textContent = rule.kind === "FORMULA" && rule.absoluteTolerance != null
                ? `${t("tolerance")} · max(${metric(rule.absoluteTolerance)}, |ƒ| × ${metric((rule.relativeTolerance || 0) * 100)}%)` : "";
            $("se-detail-validation").textContent = rule.validationConfidence == null ? "" : fill("validationDetail", {
                rate:rule.validationConfidence * 100, count:rule.validationRows
            });
            renderStats();
        }
        function svgNode(tag, attributes = {}, text) {
            const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
            for (const [key, value] of Object.entries(attributes)) el.setAttribute(key, String(value));
            if (text != null) el.textContent = text;
            return el;
        }
        const chartWidth = () => innerWidth <= 700 ? 480 : 720;
        function chartShell() {
            const svg = svgNode("svg", {viewBox: `0 0 ${chartWidth()} 410`, role: "img", "aria-label": t(rule.kind === "FORMULA" ? "formulaGraph" : "conditionGraph")});
            $("se-chart").replaceChildren(svg); return svg;
        }
        function renderChart() {
            $("se-graph-title").textContent = t(rule.kind === "FORMULA" ? "formulaGraph" : "conditionGraph");
            $("se-graph-hint").textContent = rule.kind === "FORMULA" && rule.detail
                ? fill(stored() ? "storedPreview" : "graphScope", {shown:rows().length, total:stored() ? rule.detail.stats.different : rule.detail.stats.applied}) : stored() ? t("storedDetailHelp") : t("barHint");
            if (!rule.detail || (!rule.detail.stats.applied && !(stored() && rule.kind === "FORMULA" && rows().length))) { $("se-chart").replaceChildren(node("p", "se-muted", t(stored() ? "countsUnknown" : "noDetail"))); return; }
            if (rule.kind === "FORMULA") scatter(); else bars();
        }
        function scatter() {
            const points = rows().filter(row => Number.isFinite(row.expected) && Number.isFinite(row.actual));
            if (!points.length) { $("se-chart").replaceChildren(node("p", "se-muted", t("noNumericPoints"))); return; }
            const svg = chartShell(), scale = Math.max(1, ...points.flatMap(row => [Math.abs(row.expected), Math.abs(row.actual)]));
            let lower = Math.min(...points.flatMap(row => [row.expected / scale, row.actual / scale]));
            let upper = Math.max(...points.flatMap(row => [row.expected / scale, row.actual / scale]));
            const pad = Math.max((upper - lower) * .07, .01); lower -= pad; upper += pad;
            const width = chartWidth(), left = 110, right = width - 72, plotWidth = right - left;
            const x = value => left + (value / scale - lower) / (upper - lower) * plotWidth;
            const y = value => 340 - (value / scale - lower) / (upper - lower) * 300;
            const ticks = width === 480 ? 3 : 4;
            for (let i = 0; i <= ticks; i++) {
                const fraction = i / ticks;
                const value = Math.max(-Number.MAX_VALUE, Math.min(Number.MAX_VALUE, (lower + (upper - lower) * fraction) * scale));
                const xx = left + fraction * plotWidth, yy = 340 - fraction * 300;
                svg.append(svgNode("line", {x1:left, y1:yy, x2:right, y2:yy, stroke:"#e5ece1"}));
                svg.append(svgNode("text", {x:left - 10, y:yy + 6, "text-anchor":"end"}, axisMetric(value)));
                svg.append(svgNode("text", {x:xx, y:367, "text-anchor":"middle"}, axisMetric(value)));
            }
            svg.append(svgNode("path", {d:`M${left} 40V340H${right}`, fill:"none", stroke:"#8ea797", "stroke-width":1.5}));
            svg.append(svgNode("line", {x1:left, y1:340, x2:right, y2:40, stroke:"#91ad82", "stroke-dasharray":"7 6", "stroke-width":2}));
            svg.append(svgNode("text", {x:left + plotWidth / 2, y:402, "text-anchor":"middle"}, t("expected")));
            svg.append(svgNode("text", {x:22, y:190, transform:"rotate(-90 22 190)", "text-anchor":"middle"}, t("actual")));
            svg.append(svgNode("circle", {cx:92, cy:15, r:5, fill:"#137b68"}), svgNode("text", {x:105, y:22}, t("match")));
            svg.append(svgNode("circle", {cx:205, cy:15, r:5, fill:"#ab533c"}), svgNode("text", {x:218, y:22}, t("different")));
            for (const row of points) {
                const circle = svgNode("circle", {cx:x(row.expected), cy:y(row.actual), r:row.id === selected ? 8 : 5,
                    class:`se-dot${row.status === "MATCH" ? "" : " is-different"}${row.id === selected ? " is-selected" : ""}`, "data-row-id":row.id});
                circle.append(svgNode("title", {}, `${t(stored() ? "storedCase" : "sourceRow")} ${row.sourceRow} · ${statusText(row.status)}`)); svg.append(circle);
            }
            svg.setAttribute("tabindex", "0");
            svg.setAttribute("role", "group");
            svg.setAttribute("aria-label", `${t("formulaGraph")}. ${t("pointHint")}`);
            svg.addEventListener("click", event => {
                const rect = svg.getBoundingClientRect();
                let closest = null, distance = 24;
                for (const row of points) {
                    const pixels = Math.hypot(event.clientX - rect.left - x(row.expected) * rect.width / width,
                        event.clientY - rect.top - y(row.actual) * rect.height / 410);
                    if (pixels <= distance) { closest = row; distance = pixels; }
                }
                if (closest) inspect(closest.id, false);
            });
            svg.addEventListener("keydown", event => {
                if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
                event.preventDefault();
                const current = points.findIndex(row => row.id === selected);
                const index = event.key === "Home" ? 0 : event.key === "End" ? points.length - 1
                    : Math.max(0, Math.min(points.length - 1, current + (["ArrowLeft", "ArrowUp"].includes(event.key) ? -1 : 1)));
                inspect(points[index].id, true);
            });
        }
        function bars() {
            const svg = chartShell(), stats = rule.detail.stats, maximum = Math.max(1, stats.applied), barWidth = chartWidth() - 140;
            svg.setAttribute("role", "group");
            for (const [index, key, count, color] of [[0,"MATCH",stats.matched,"#137b68"], [1,"DIFFERENT",stats.different,"#ab533c"]]) {
                const group = svgNode("g", {"data-bar-filter":key, role:"button", tabindex:0, "aria-label":`${t(key === "MATCH" ? "match" : "different")} ${number(count)}`});
                group.append(svgNode("rect", {x:10, y:60 + index * 130, width:chartWidth() - 20, height:105, fill:"transparent"}));
                group.append(svgNode("text", {x:20, y:86 + index * 130}, t(key === "MATCH" ? "match" : "different")));
                group.append(svgNode("rect", {x:20, y:105 + index * 130, width:barWidth, height:42, rx:8, fill:"#eef2e8"}));
                group.append(svgNode("rect", {x:20, y:105 + index * 130, width:Math.max(0, count / maximum * barWidth), height:42, rx:8, fill:color}));
                group.append(svgNode("text", {x:barWidth + 40, y:134 + index * 130}, number(count)));
                group.addEventListener("click", () => setFilter(key));
                group.addEventListener("keydown", event => { if (["Enter", " "].includes(event.key)) { event.preventDefault(); setFilter(key); } });
                svg.append(group);
            }
        }
        function inspect(id, keyboard) {
            const row = rows().find(row => row.id === id); if (!row) return;
            selected = id;
            if (tab === "graph" && rule.kind === "FORMULA") {
                renderChart();
                if (keyboard) $("se-chart").querySelector("svg")?.focus({preventScroll:true});
            }
            renderInspector();
            if (tab === "data") {
                renderTable();
                if (keyboard) [...$("se-data-table").querySelectorAll("tr[data-row-id]")].find(tr => tr.dataset.rowId === String(selected))?.focus({preventScroll:true});
            }
        }
        function renderInspector() {
            const inspector = $("se-row-inspector"), row = rows().find(row => row.id === selected);
            inspector.replaceChildren(); inspector.hidden = !row;
            if (!row) return;
            inspector.append(node("h3", "", `${t(stored() ? "storedCase" : "sourceRow")} ${stored() ? row.sourceRow : number(row.sourceRow)} · ${statusText(row.status)}`));
            const grid = node("dl", "se-inspector-grid");
            const fields = [...(rule.detail.inputs || []).map(column => [column.label, row.values[column.key]]),
                [`${t("actual")} · ${rule.detail.target.label}`, row.values[rule.detail.target.key]]];
            if (rule.kind === "FORMULA") fields.push([t("expected"), metric(row.expected)], [t("residual"), metric(row.residual)]);
            for (const [label, value] of fields) { const div = node("div", ""); div.append(node("dt", "", label), node("dd", "", value ?? "—")); grid.append(div); }
            inspector.append(grid);
            const pane = $(tab === "graph" ? "se-detail-graph" : "se-detail-data");
            if (tab === "data") pane.insertBefore(inspector, $("se-data-table")); else pane.append(inspector);
        }
        function columns() {
            const detail = rule.detail;
            const result = [{label:t(stored() ? "storedCase" : "sourceRow"), value:row => row.sourceRow},
                ...(detail?.inputs || []).map(column => ({label:column.label, value:row => row.values[column.key]}))];
            if (rule.kind === "FORMULA") result.push({label:t("expected"), value:row => row.expected});
            result.push({label:detail ? `${t("actual")} · ${detail.target.label}` : t("actual"), value:row => row.values[detail.target.key]});
            if (rule.kind === "FORMULA") result.push({label:t("residual"), value:row => row.residual});
            result.push({label:t("rowStatus"), value:row => statusText(row.status)});
            return result;
        }
        function renderTable() {
            const available = filtered(), pages = Math.max(1, Math.ceil(available.length / pageSize));
            page = Math.min(page, pages - 1);
            const table = node("table", ""), head = node("thead", ""), tr = node("tr", ""), defs = columns();
            for (const definition of defs) tr.append(node("th", "", definition.label));
            head.append(tr); table.append(head);
            const body = node("tbody", "");
            for (const row of available.slice(page * pageSize, (page + 1) * pageSize)) {
                const tr = node("tr", `se-data-row${selected === row.id ? " is-selected" : ""}`); tr.dataset.rowId = row.id; tr.tabIndex = 0;
                for (const definition of defs) {
                    const raw = definition.value(row), value = typeof raw === "number" ? metric(raw) : raw ?? "—";
                    const td = node("td", "", value); td.title = String(value); tr.append(td);
                }
                tr.addEventListener("click", () => inspect(row.id));
                tr.addEventListener("keydown", event => { if (event.key === "Enter") inspect(row.id, true); });
                body.append(tr);
            }
            table.append(body);
            $("se-data-table").replaceChildren(available.length ? table : node("p", "se-muted", t("noRows")));
            $("se-data-page").textContent = `${page + 1} / ${pages}`;
            $("se-data-prev").disabled = page === 0;
            $("se-data-next").disabled = page + 1 >= pages;
            $("se-data-download").disabled = !available.length;
            $("se-data-scope").textContent = rule.detail
                ? fill(stored() ? "storedPreview" : "detailScope", {shown:rows().length, total:stored() ? rule.detail.stats.different : rule.detail.stats.applied}) + (rule.detail.truncatedCells ? ` ${t("clippedCells")}` : "") : t("noDetail");
        }
        function setFilter(next) { filter = next; page = 0; selected = null; setTab("data"); }
        function setTab(next, focus = false) {
            tab = next;
            if (next === "data" && selected != null) {
                if (!filtered().some(row => row.id === selected)) filter = "ALL";
                page = Math.floor(Math.max(0, filtered().findIndex(row => row.id === selected)) / pageSize);
            }
            document.querySelectorAll("[data-detail-tab]").forEach(button => {
                const active = button.dataset.detailTab === next;
                button.setAttribute("aria-selected", String(active)); button.tabIndex = active ? 0 : -1;
                if (active && focus) button.focus();
            });
            $("se-detail-graph").hidden = next !== "graph";
            $("se-detail-data").hidden = next !== "data";
            document.querySelectorAll("[data-row-filter]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.rowFilter === filter)));
            if (next === "graph") renderChart(); else renderTable();
            renderInspector();
        }
        function csvCell(value) {
            let text = value == null ? "" : String(value);
            if (/^[\s]*[=+@\-]/.test(text) && !/^-?\d+(?:\.\d+)?(?:e[+-]?\d+)?$/i.test(text)) text = "'" + text;
            return '"' + text.replaceAll('"', '""') + '"';
        }
        $("se-detail-back").addEventListener("click", onBack);
        document.querySelectorAll("[data-detail-tab]").forEach(button => {
            button.addEventListener("click", () => setTab(button.dataset.detailTab));
            button.addEventListener("keydown", event => {
                if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
                    event.preventDefault(); setTab(event.key === "Home" ? "graph" : event.key === "End" ? "data" : tab === "graph" ? "data" : "graph", true);
                }
            });
        });
        document.querySelectorAll("[data-row-filter]").forEach(button => button.addEventListener("click", () => setFilter(button.dataset.rowFilter)));
        $("se-data-prev").addEventListener("click", () => { page--; renderTable(); });
        $("se-data-next").addEventListener("click", () => { page++; renderTable(); });
        $("se-data-download").addEventListener("click", () => {
            const defs = columns(), lines = [defs.map(column => csvCell(column.label)).join(","),
                ...filtered().map(row => defs.map(column => csvCell(column.value(row))).join(","))];
            const url = URL.createObjectURL(new Blob(["\ufeff" + lines.join("\r\n")], {type:"text/csv;charset=utf-8"}));
            const link = node("a", ""); link.href = url; link.download = stored() ? "Key_Rules_stored_violations.csv" : "Rule_Discovery_analyzed_sample.csv";
            document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
        });
        function clear() {
            rule = null; selected = null;
            for (const id of ["se-detail-title", "se-detail-condition", "se-detail-stats", "se-detail-tolerance", "se-detail-validation", "se-chart", "se-row-inspector", "se-data-table", "se-data-scope"]) $(id).replaceChildren();
            $("se-row-inspector").hidden = true;
        }
        let resizeFrame = null;
        window.addEventListener("resize", () => {
            cancelAnimationFrame(resizeFrame);
            if (rule && tab === "graph") resizeFrame = requestAnimationFrame(() => { if (rule && tab === "graph") renderChart(); });
        });
        return {
            show(next) { rule = {...next, detail:["ANALYZED_SAMPLE","STORED_DETECTION"].includes(next.detail?.cohort) ? next.detail : null}; tab = "graph"; filter = "ALL"; page = 0; selected = null; renderOverview(); setTab("graph"); },
            refresh() { if (rule) { renderOverview(); setTab(tab); } },
            clear
        };
    };
})();
