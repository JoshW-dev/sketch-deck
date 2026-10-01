// Usage: npm run new -- <slug> "Video title"
import fs from 'node:fs';
import path from 'node:path';

const [slug, title = 'Untitled video'] = process.argv.slice(2);
if (!slug || !/^[a-z0-9-]+$/.test(slug)) {
  console.error('Usage: npm run new -- <slug> "Video title"   (slug: lowercase letters, numbers, dashes)');
  process.exit(1);
}
const dir = path.resolve('videos', slug);
if (fs.existsSync(dir)) { console.error(`videos/${slug} already exists`); process.exit(1); }

fs.mkdirSync(dir, { recursive: true });
for (const f of ['index.html', 'content.js']) {
  const src = fs.readFileSync(path.resolve('templates/video', f), 'utf8');
  fs.writeFileSync(path.join(dir, f), src.replaceAll('__TITLE__', title));
}
fs.writeFileSync(path.join(dir, 'outline.md'), `# ${title}\n\nThe one-sentence point:\n\nParts (about 50 seconds and 5 steps each):\n\n1.\n2.\n3.\n`);
console.log(`Created videos/${slug}. Open videos/${slug}/index.html in Chrome, then edit content.js.`);
