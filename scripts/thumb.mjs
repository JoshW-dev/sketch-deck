// Usage: npm run thumb -- <slug> [variant ...]
// Renders videos/<slug>/thumbnail.html#<variant> to videos/<slug>/thumbnail-<variant>.png at 1280x720,
// the size YouTube asks for. Defaults to variant a. Uses your installed Chrome, headless.
import { chromium } from 'playwright-core';
import { pathToFileURL } from 'node:url';
import fs from 'node:fs';
import path from 'node:path';

const [slug, ...variants] = process.argv.slice(2);
const file = slug && path.resolve('videos', slug, 'thumbnail.html');
if (!slug || !fs.existsSync(file)) {
  console.error('Usage: npm run thumb -- <slug> [variant ...]   (needs videos/<slug>/thumbnail.html)');
  process.exit(1);
}

const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
for (const v of variants.length ? variants : ['a']) {
  await page.goto(`${pathToFileURL(file).href}#${v}`);
  await page.reload();
  await page.waitForSelector('body[data-ready="1"]');
  await page.waitForTimeout(300);
  const out = path.resolve('videos', slug, `thumbnail-${v}.png`);
  await page.screenshot({ path: out });
  const kb = Math.round(fs.statSync(out).size / 1024);
  console.log(`${path.relative(process.cwd(), out)} (${kb} KB${kb > 2048 ? ', over the 2 MB YouTube limit' : ''})`);
}
await browser.close();
