// Usage: npm run open -- <slug>   Opens videos/<slug>/index.html in Chrome (macOS), or the default browser elsewhere.
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const slug = process.argv[2];
const file = slug && path.resolve('videos', slug, 'index.html');
if (!slug || !fs.existsSync(file)) {
  const have = fs.readdirSync('videos').join(', ');
  console.error(`Usage: npm run open -- <slug>   (videos: ${have})`);
  process.exit(1);
}
if (process.platform === 'darwin') {
  try { execFileSync('open', ['-a', 'Google Chrome', file]); } catch { execFileSync('open', [file]); }
} else {
  execFileSync(process.platform === 'win32' ? 'explorer' : 'xdg-open', [file]);
}
console.log(`Opened videos/${slug}. Click the page, then press F for full screen.`);
