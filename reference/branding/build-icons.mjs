import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const assets = path.join(root, 'frontend/assets');
const logo = await fs.readFile(path.join(assets, 'ineditaone_compact_en.svg'), 'utf8');
const mark = logo.match(/<path\b[^>]*\/>/g);
if (mark?.length !== 2) throw new Error('Expected the two paths of the IN-EDITAONE check mark.');
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="192" height="192" viewBox="0 0 192 192" role="img" aria-label="인에디타원 IN-EDITAONE">
<title>인에디타원 · IN-EDITAONE</title>
<rect width="192" height="192" rx="40" fill="#172b45"/>
<g fill="#ffffff" transform="translate(-623 18)">${mark.join('')}</g>
</svg>
`;
await fs.writeFile(path.join(assets, 'ineditaone-icon.svg'), svg, 'utf8');

const icoSizes = [16, 24, 32, 48, 64, 128, 256];
const pngSizes = [32, 180, 192, 512];
const rasters = new Map();
const browser = await chromium.launch({ headless: true });
try {
    const page = await browser.newPage({ deviceScaleFactor: 1 });
    for (const size of [...new Set([...icoSizes, ...pngSizes])]) {
        await page.setViewportSize({ width: size, height: size });
        await page.setContent(`<html><body style="margin:0;background:transparent">${svg.replace('width="192" height="192"', `width="${size}" height="${size}"`)}</body></html>`);
        const png = await page.screenshot({ omitBackground: true });
        rasters.set(size, png);
        if (pngSizes.includes(size)) await fs.writeFile(path.join(assets, `ineditaone-icon-${size}.png`), png);
    }
} finally {
    await browser.close();
}

// ICO stores a directory followed by PNG frames, including a 256px Windows icon.
const header = Buffer.alloc(6 + icoSizes.length * 16);
header.writeUInt16LE(1, 2);
header.writeUInt16LE(icoSizes.length, 4);
let offset = header.length;
for (const [index, size] of icoSizes.entries()) {
    const entry = 6 + index * 16;
    const png = rasters.get(size);
    header[entry] = header[entry + 1] = size === 256 ? 0 : size;
    header.writeUInt16LE(1, entry + 4);
    header.writeUInt16LE(32, entry + 6);
    header.writeUInt32LE(png.length, entry + 8);
    header.writeUInt32LE(offset, entry + 12);
    offset += png.length;
}
await fs.writeFile(path.join(root, 'frontend/favicon.ico'), Buffer.concat([header, ...icoSizes.map(size => rasters.get(size))]));
console.log('IN-EDITAONE SVG, PNG and Windows ICO icons generated.');
