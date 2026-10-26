import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const output = path.join(root, 'tmp/branding-qa');
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
try {
    for (const [width, language] of [[1440, 'ko'], [430, 'en']]) {
        const page = await browser.newPage({ viewport: { width, height: 1000 } });
        const errors = [], missing = [];
        page.on('pageerror', error => errors.push(error.message));
        await page.addInitScript(language => sessionStorage.setItem('initLanguageCode', language), language);
        await page.route('**/*', async route => {
            const url = new URL(route.request().url());
            if (url.origin !== 'http://branding.test') return route.abort();
            if (url.pathname.startsWith('/api/')) {
                if (url.pathname.endsWith('/session/me')) return route.fulfill({ status: 401, json: { detail: 'Login required' } });
                return route.fulfill({ json: { status: 'success', data: [], setupCompleted: true, adminExists: true } });
            }
            const base = path.join(root, 'frontend');
            const local = path.resolve(base, '.' + (url.pathname === '/' ? '/index.html' : url.pathname));
            if (!local.startsWith(base + path.sep)) return route.abort();
            try {
                const body = await fs.readFile(local);
                const mime = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml', '.woff2': 'font/woff2' }[path.extname(local)] || 'application/octet-stream';
                return route.fulfill({ body, contentType: mime });
            } catch {
                missing.push(url.pathname);
                return route.fulfill({ status: 404, body: '' });
            }
        });
        await page.goto('http://branding.test/');
        await page.waitForFunction(() => window.PageManager?.readyPages.has('login'));
        await page.evaluate(async language => { await window.login.changeLoginLanguage(language); }, language);
        await page.evaluate(async language => { await window.login.changeLoginLanguage(language); }, language);
        await page.evaluate(async () => { await document.fonts.ready; });
        const text = await page.locator('body').innerText();
        assert(!/IN-DEPS|인뎁스|INIT-Data Editing/.test(text));
        assert.match(text, language === 'ko' ? /인에디타원/ : /IN-EDITAONE/);
        assert.deepEqual(errors, []);
        assert.deepEqual(missing.filter(value => !value.includes('favicon')), []);
        assert.equal(await page.locator('img[src*="ineditaone"]').evaluateAll(images => images.every(img => img.complete && img.naturalWidth > 0)), true);
        await page.screenshot({ path: path.join(output, `login-${width}-${language}.png`), fullPage: true });
        await page.goto('http://branding.test/help/in-editaone-system-guide.html');
        assert.match(await page.title(), /IN-EDITAONE/);
        assert.equal(await page.locator('img').evaluateAll(images => images.every(img => img.complete && img.naturalWidth > 0)), true);
        await page.screenshot({ path: path.join(output, `guide-${width}-${language}.png`), fullPage: false });
        await page.goto('http://branding.test/help/in-deps-system-guide.html');
        await page.waitForURL('**/in-editaone-system-guide.html');
        assert.deepEqual(errors, []);
        await page.close();
    }
    console.log('Branding browser checks passed: Korean/English, desktop/mobile, logos, help and old URL redirect.');
} finally { await browser.close(); }
