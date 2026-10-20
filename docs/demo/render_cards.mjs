// Renders the demo video's cards to PNG: node docs/demo/render_cards.mjs <out-dir> [r=..] [h=..]
// Needs Playwright (npm i playwright) and a Chromium.
import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const out = process.argv[2] || '.';
const extra = process.argv.slice(3).join('&');
const page = path.join(path.dirname(fileURLToPath(import.meta.url)), 'cards.html');
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
const p = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
for (const card of ['title', 'how', 'results', 'end']) {
  await p.goto(`file://${page}?card=${card}${extra ? '&' + extra : ''}`);
  await p.waitForTimeout(800);
  await p.screenshot({ path: path.join(out, `card-${card}.png`) });
  console.log('card', card);
}
await browser.close();
