import fs from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const root = path.resolve(import.meta.dirname, '..');
const pages = new Map([
    ['/', 'frontend/index.html'],
    ['/quick-edit/', 'quick-edit/index.html'],
    ['/simple-edit/', 'simple-edit/index.html'],
    ...['report-viewer.html', 'help/home.html', 'help/page.html', 'help/in-editaone-system-guide.html', 'help/in-deps-system-guide.html'].map(name => [`/${name}`, `frontend/${name}`])
]);
const mime = { '.html': 'text/html; charset=utf-8', '.ico': 'image/x-icon', '.svg': 'image/svg+xml', '.png': 'image/png', '.webmanifest': 'application/manifest+json' };
const server = http.createServer(async (req, res) => {
    try {
        const url = new URL(req.url, 'http://localhost');
        const file = pages.get(url.pathname) ?? (url.pathname.startsWith('/assets/ineditaone-icon') || ['/favicon.ico', '/site.webmanifest'].includes(url.pathname) ? `frontend${url.pathname}` : null);
        if (!file || file.includes('..')) { res.writeHead(404).end(); return; }
        res.writeHead(200, { 'Content-Type': mime[path.extname(file)] });
        res.end(await fs.readFile(path.join(root, file)));
    } catch { res.writeHead(500).end(); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
let browser;
try {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ javaScriptEnabled: false });
    const page = await context.newPage();
    for (const url of pages.keys()) {
        await page.goto(origin + url);
        if (url === '/help/in-deps-system-guide.html') {
            await page.waitForURL('**/help/in-editaone-system-guide.html');
            await page.waitForLoadState('load');
        }
        const links = await page.locator('link[rel="icon"]').evaluateAll(nodes => nodes.map(n => n.href));
        assert.equal(links.length, 2, url);
        for (const href of links) {
            const response = await context.request.get(href);
            assert.equal(response.status(), 200, href);
            assert.match(response.headers()['content-type'], /^image\//);
        }
    }
    for (const size of [32, 180, 192, 512]) {
        const response = await context.request.get(`${origin}/assets/ineditaone-icon-${size}.png`);
        assert.equal(response.status(), 200);
        const png = await response.body();
        assert.equal(png.toString('hex', 0, 8), '89504e470d0a1a0a');
        assert.equal(png.readUInt32BE(16), size);
        assert.equal(png.readUInt32BE(20), size);
    }
    const manifestResponse = await context.request.get(`${origin}/site.webmanifest`);
    const manifest = await manifestResponse.json();
    assert.equal(manifest.short_name, '인에디타원');
    for (const icon of manifest.icons) assert.equal((await context.request.get(origin + icon.src)).status(), 200);
    const ico = await fs.readFile(path.join(root, 'frontend/favicon.ico'));
    assert.equal(ico.readUInt16LE(2), 1);
    assert.equal(ico.readUInt16LE(4), 7);
    for (let index = 0; index < 7; index++) {
        const entry = 6 + index * 16;
        const size = ico[entry] || 256;
        const offset = ico.readUInt32LE(entry + 12);
        assert.equal(ico.toString('hex', offset, offset + 8), '89504e470d0a1a0a');
        assert.equal(ico.readUInt32BE(offset + 16), size);
        assert.equal(ico.readUInt32BE(offset + 20), size);
        assert.ok(offset + ico.readUInt32LE(entry + 8) <= ico.length);
    }
    console.log(`PASS: ${pages.size} browser pages, SVG/ICO responses, 4 PNG dimensions, manifest icons, 7 ICO frames. No application or DB started.`);
} finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
}
