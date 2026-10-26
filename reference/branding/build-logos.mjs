import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const output = path.join(root, 'frontend/assets');
const navy = '#172b45';
const tagline = 'INIT One-Stop Data Editing&amp;Imputation Solution';
const browser = await chromium.launch({ headless: true });
try {
    const page = await browser.newPage({ viewport: { width: 1200, height: 320 }, deviceScaleFactor: 2 });
    for (const kind of ['compact', 'banner']) {
        for (const variant of ['en', 'ko', 'bilingual', ...(kind === 'compact' ? ['en_white'] : [])]) {
            const color = variant === 'en_white' ? '#ffffff' : navy;
            const banner = kind === 'banner';
            const height = banner ? 310 : 280;
            const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="${height}" viewBox="0 0 1000 ${height}" role="img" aria-label="IN-EDITAONE 인에디타원">
<title>IN-EDITAONE · 인에디타원</title>
<desc>INIT One-Stop Data Editing&amp;Imputation Solution</desc>
<g fill="${color}" font-family="Arial, sans-serif" font-weight="750">
<text x="18" y="133" font-size="150" textLength="632" lengthAdjust="spacingAndGlyphs">iNEdita</text>
<path d="M721 21 C677 21 655 46 655 80 C655 116 677 137 714 137 C752 137 775 113 775 79 L775 61 L754 84 C751 107 739 118 714 118 C690 118 677 104 677 79 C677 55 691 40 714 40 C722 40 730 42 737 46 L752 29 C743 24 732 21 721 21 Z"/>
<path d="M692 58 L712 79 L767 16 L778 27 L712 105 L680 73 Z"/>
<text x="775" y="133" font-size="150" textLength="207" lengthAdjust="spacingAndGlyphs">ne</text>
</g>
<text x="${banner ? 22 : 500}" y="${banner ? 211 : 254}" fill="${color}" font-family="Malgun Gothic, sans-serif" font-size="${banner ? 58 : 104}" font-weight="700" text-anchor="${banner ? 'start' : 'middle'}">인에디타원</text>
${banner ? `<text x="22" y="285" fill="${color}" font-family="Arial, sans-serif" font-size="40" font-weight="500" textLength="956" lengthAdjust="spacingAndGlyphs">${tagline}</text>` : ''}
</svg>`;
            const basename = `ineditaone_${kind}_${variant}`;
            await fs.writeFile(path.join(output, `${basename}.svg`), svg, 'utf8');
            await page.setViewportSize({ width: 1000, height });
            await page.setContent(`<html><body style="margin:0;background:transparent">${svg}</body></html>`);
            await page.screenshot({ path: path.join(output, `${basename}.png`), omitBackground: true });
            // Existing database URLs and bookmarks keep resolving to the new artwork.
            await fs.copyFile(path.join(output, `${basename}.png`), path.join(output, `indeps_${kind}_${variant}.png`));
        }
    }
} finally {
    await browser.close();
}
console.log('IN-EDITAONE vector and PNG logos generated.');
