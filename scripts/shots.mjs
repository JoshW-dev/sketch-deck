// Usage: npm run shots -- <slug> [--gif <part number>]
// Writes docs/screenshots/<slug>/: board-start.png, part-N.png for every part, board.png,
// and with --gif a GIF of that part building step by step. Uses your installed Chrome, headless.
import { chromium } from 'playwright-core';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const args = process.argv.slice(2);
const slug = args[0];
const gifPart = args.includes('--gif') ? Number(args[args.indexOf('--gif') + 1]) : null;
const deckFile = slug && path.resolve('videos', slug, 'index.html');
if (!slug || !fs.existsSync(deckFile)) {
  console.error('Usage: npm run shots -- <slug> [--gif <part number>]');
  process.exit(1);
}
const url = pathToFileURL(deckFile).href;
const out = path.resolve('docs/screenshots', slug);
fs.mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });

async function open(contextOptions) {
  const ctx = await browser.newContext(contextOptions);
  const page = await ctx.newPage();
  const created = Date.now();
  await page.goto(url);
  await page.waitForFunction(() => window.deck?.ready);
  await page.keyboard.press('h'); // hide the step counter
  return { ctx, page, created };
}

// stills at 1920x1080
{
  const { ctx, page } = await open({ viewport: { width: 1920, height: 1080 } });
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${out}/board-start.png` });
  const n = await page.evaluate(() => deck.parts.length);
  for (let k = 0; k < n; k++) {
    await page.evaluate(k => deck.enter(k, 'max'), k);
    await page.waitForTimeout(700);
    await page.screenshot({ path: `${out}/part-${k + 1}.png` });
  }
  await page.evaluate(() => deck.seeAll());
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${out}/board.png` });
  await ctx.close();
  console.log(`stills: ${n + 2} files in docs/screenshots/${slug}/`);
}

// one part building, as a GIF
if (gifPart) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'sketch-deck-'));
  const size = { width: 1280, height: 720 };
  const { ctx, page, created } = await open({ viewport: size, recordVideo: { dir: tmp, size } });
  await page.evaluate(k => deck.enter(k, 0), gifPart - 1);
  await page.waitForTimeout(600);
  const skip = (Date.now() - created) / 1000;
  const max = await page.evaluate(k => deck.parts[k].max, gifPart - 1);
  for (let i = 0; i < max; i++) {
    await page.keyboard.press('ArrowRight');
    await page.waitForTimeout(2000);
  }
  await page.waitForTimeout(600);
  const video = page.video();
  await ctx.close();
  const webm = await video.path();
  const gif = `${out}/part-${gifPart}.gif`;
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-ss', skip.toFixed(2), '-i', webm, '-vf',
    'fps=15,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle',
    '-loop', '0', gif]);
  fs.rmSync(tmp, { recursive: true, force: true });
  console.log(`gif: docs/screenshots/${slug}/part-${gifPart}.gif`);
}

await browser.close();
