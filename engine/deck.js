/* sketch-deck engine
   A video's content.js calls startDeck({ board, parts }). See README.md for the content API.
   Canvas is 1920x1080. The camera box goes on the right in the edit, so content stays left of x 1540. */

/* ---------- palette (Excalidraw's open-color set) ---------- */
const INK = '#1e1e1e', GRAY = '#868e96', LIGHT = '#ced4da';
const PAL = {
  orange: ['#e8590c', '#ffd8a8'],
  yellow: ['#f08c00', '#ffec99'],
  green:  ['#2f9e44', '#b2f2bb'],
  blue:   ['#1971c2', '#a5d8ff'],
  purple: ['#6741d9', '#d0bfff'],
  red:    ['#e03131', '#ffc9c9'],
  teal:   ['#0c8599', '#96f2d7'],
};
const RED = PAL.red[0], GREEN = PAL.green[0];

/* ---------- builder: rough.js shapes grouped into reveal units ---------- */
const NS = 'http://www.w3.org/2000/svg';
function mk(tag, attrs, parent) {
  const e = document.createElementNS(NS, tag);
  if (attrs) for (const k in attrs) if (attrs[k] != null) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}
function rrPath(x, y, w, h, r) {
  return `M${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + h - r} Q${x + w},${y + h} ${x + w - r},${y + h} H${x + r} Q${x},${y + h} ${x},${y + h - r} V${y + r} Q${x},${y} ${x + r},${y} Z`;
}

class Builder {
  constructor(svg, seed) { this.svg = svg; this.rc = rough.svg(svg); this.s = 0; this.seed = seed; this.units = []; this.target = null; }
  at(n) { this.s = n; return this; }
  opts(o = {}) {
    return {
      roughness: o.rough ?? 1, bowing: o.bow ?? 1, stroke: o.stroke ?? INK, strokeWidth: o.sw ?? 2,
      fill: o.fill, fillStyle: o.fillStyle ?? 'solid', hachureGap: o.gap ?? 8, hachureAngle: -41, fillWeight: 1.6,
      strokeLineDash: o.dash, seed: this.seed++,
    };
  }
  put(node, o, anim) {
    if (this.target) { this.target.appendChild(node); return node; }
    const g = mk('g', { class: 'u' }, this.svg);
    g.appendChild(node);
    this.reg(g, o, anim);
    return g;
  }
  reg(g, o, anim) {
    g._s = o.s ?? this.s; g._until = o.until ?? Infinity; g._anim = o.anim ?? anim; g._delay = o.delay; g._state = 'shown';
    this.units.push(g);
  }
  group(o, fn) {
    if (typeof o === 'function') { fn = o; o = {}; }
    const g = mk('g');
    const prev = this.target;
    this.target = g; fn(); this.target = prev;
    if (prev) { prev.appendChild(g); return g; }
    g.setAttribute('class', 'u'); this.svg.appendChild(g); this.reg(g, o, 'draw');
    return g;
  }

  // ---- primitives ----
  rect(x, y, w, h, o = {}) {
    const r = o.r ?? Math.min(14, w / 4, h / 4);
    const n = r > 0 ? this.rc.path(rrPath(x, y, w, h, r), this.opts(o)) : this.rc.rectangle(x, y, w, h, this.opts(o));
    return this.put(n, o, 'draw');
  }
  ellipse(cx, cy, w, h, o = {}) { return this.put(this.rc.ellipse(cx, cy, w, h, this.opts(o)), o, 'draw'); }
  line(x1, y1, x2, y2, o = {}) { return this.put(this.rc.line(x1, y1, x2, y2, this.opts(o)), o, 'draw'); }
  lpath(pts, o = {}) { return this.put(this.rc.linearPath(pts, this.opts(o)), o, 'draw'); }
  poly(pts, o = {}) { return this.put(this.rc.polygon(pts, this.opts(o)), o, 'draw'); }
  path(d, o = {}) { return this.put(this.rc.path(d, this.opts(o)), o, 'draw'); }
  arrow(x1, y1, x2, y2, o = {}) {
    const a = Math.atan2(y2 - y1, x2 - x1), h = o.head ?? 16, sp = 0.5;
    const n = mk('g');
    n.appendChild(this.rc.line(x1, y1, x2, y2, this.opts(o)));
    n.appendChild(this.rc.linearPath([[x2 - h * Math.cos(a - sp), y2 - h * Math.sin(a - sp)], [x2, y2], [x2 - h * Math.cos(a + sp), y2 - h * Math.sin(a + sp)]], this.opts({ ...o, rough: 0.6, dash: undefined })));
    return this.put(n, o, 'draw');
  }
  curveArrow(pts, o = {}) {
    const n = mk('g');
    n.appendChild(this.rc.curve(pts, this.opts(o)));
    const [p, q] = pts.slice(-2), a = Math.atan2(q[1] - p[1], q[0] - p[0]), h = o.head ?? 16, sp = 0.5;
    n.appendChild(this.rc.linearPath([[q[0] - h * Math.cos(a - sp), q[1] - h * Math.sin(a - sp)], q, [q[0] - h * Math.cos(a + sp), q[1] - h * Math.sin(a + sp)]], this.opts({ ...o, rough: 0.6, dash: undefined })));
    return this.put(n, o, 'draw');
  }
  text(x, y, str, o = {}) {
    const size = o.size ?? 30;
    const t = mk('text', { x, y, 'font-family': o.mono ? 'Comic Shanns' : 'Excalifont', 'font-size': size, fill: o.color ?? INK, 'text-anchor': o.anchor ?? 'start' });
    String(str).split('\n').forEach((ln, i) => {
      const ts = mk('tspan', { x, dy: i ? Math.round(size * (o.lh ?? 1.25)) : 0 }, t);
      ts.textContent = ln; ts._full = ln;
    });
    return this.put(t, o, 'type');
  }
  bar(x, y, w, h, o = {}) {
    const r = mk('rect', { class: 'bar', x, y, width: w, height: h, rx: o.rx ?? 10, fill: o.fill ?? '#fff', stroke: o.stroke ?? INK, 'stroke-width': o.sw ?? 2 });
    r._w = w; r._from = o.from ?? 0;
    return this.put(r, o, 'grow');
  }
  check(x, y, sz = 32, o = {}) {
    return this.lpath([[x, y + sz * 0.55], [x + sz * 0.38, y + sz * 0.92], [x + sz, y]], { ...o, stroke: o.color ?? GREEN, sw: o.sw ?? 3.4, rough: o.rough ?? 0.8 });
  }
  cross(x, y, sz = 28, o = {}) {
    const n = mk('g'), c = o.color ?? RED;
    n.appendChild(this.rc.line(x, y, x + sz, y + sz, this.opts({ ...o, stroke: c, sw: 3 })));
    n.appendChild(this.rc.line(x + sz, y, x, y + sz, this.opts({ ...o, stroke: c, sw: 3 })));
    return this.put(n, o, 'draw');
  }

  // ---- small drawings ----
  sparkle(cx, cy, r, o = {}) {
    const k = r * 0.28;
    const d = `M${cx},${cy - r} Q${cx + k},${cy - k} ${cx + r},${cy} Q${cx + k},${cy + k} ${cx},${cy + r} Q${cx - k},${cy + k} ${cx - r},${cy} Q${cx - k},${cy - k} ${cx},${cy - r} Z`;
    return this.path(d, { rough: 0.4, sw: 1.5, ...o, fill: o.fill ?? '#fab005' });
  }
  tag(x, y, label, o = {}) {
    const plain = o.spark === false;
    const w = o.w ?? Math.round(label.length * 13.4 + (plain ? 34 : 62));
    return this.group({ anim: 'pop', ...o }, () => {
      this.rect(x, y, w, 46, { fill: o.fill ?? PAL.yellow[1], sw: 1.6, r: 12 });
      if (!plain) this.sparkle(x + 25, y + 23, 11, { fill: o.sparkFill ?? '#fab005' });
      this.text(x + (plain ? 17 : 45), y + 31, label, { mono: true, size: 22 });
    });
  }
  doc(x, y, w, h, o = {}) {
    return this.group(o, () => {
      const f = Math.min(w, h) * 0.28;
      this.path(`M${x},${y} H${x + w - f} L${x + w},${y + f} V${y + h} H${x} Z`, { fill: o.fill ?? '#fff' });
      this.lpath([[x + w - f, y], [x + w - f, y + f], [x + w, y + f]], { sw: 1.6 });
      for (let i = 0; i < (o.lines ?? 3); i++) {
        const yy = y + h * (0.42 + i * 0.17);
        this.line(x + w * 0.18, yy, x + w * (i === 2 ? 0.62 : 0.82), yy, { sw: 1.4, stroke: GRAY });
      }
    });
  }
  clock(cx, cy, r) {
    return this.group(() => {
      this.ellipse(cx, cy, r * 2, r * 2, { fill: '#fff' });
      this.lpath([[cx, cy - r * 0.62], [cx, cy], [cx + r * 0.45, cy + r * 0.2]], { sw: 2, rough: 0.5 });
    });
  }
  person(x, y) {
    return this.group(() => {
      this.ellipse(x, y, 46, 46, { fill: '#fff' });
      this.line(x, y + 23, x, y + 100);
      this.line(x, y + 48, x - 34, y + 84);
      this.line(x, y + 48, x + 40, y + 28);
      this.line(x, y + 100, x - 26, y + 152);
      this.line(x, y + 100, x + 26, y + 152);
    });
  }
  bubble(x, y, w, h, str, o = {}) {
    const r = 18;
    const d = `M${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + h - r} Q${x + w},${y + h} ${x + w - r},${y + h} H${x + 86} L${x + 26},${y + h + 40} L${x + 52},${y + h} H${x + r} Q${x},${y + h} ${x},${y + h - r} V${y + r} Q${x},${y} ${x + r},${y} Z`;
    const size = o.size ?? 30, lines = str.split('\n');
    return this.group(o, () => {
      this.path(d, { fill: o.fill ?? PAL.blue[1] });
      const top = y + h / 2 - ((lines.length - 1) * size * 1.2) / 2 + size * 0.33;
      this.text(x + w / 2, top, str, { anchor: 'middle', size, lh: 1.2 });
    });
  }
  callout(x, y, w, h, str, o = {}) {
    return this.group(o, () => {
      this.rect(x, y, w, h, { fill: o.fill ?? PAL.yellow[1], r: 16 });
      this.text(x + w / 2, y + h / 2 + (o.size ?? 40) * 0.33, str, { anchor: 'middle', size: o.size ?? 40 });
    });
  }
}

function fixAnchors(svg) {
  svg.querySelectorAll('text').forEach(t => {
    const a = t.getAttribute('text-anchor');
    if (!a || a === 'start') return;
    t.querySelectorAll('tspan').forEach(ts => {
      const x = +ts.getAttribute('x'), w = ts.getComputedTextLength();
      ts.setAttribute('x', a === 'middle' ? x - w / 2 : x - w);
    });
    t.setAttribute('text-anchor', 'start');
  });
}

function header(b, n, title, color) {
  const [ink, fill] = PAL[color] ?? PAL.blue;
  const probe = mk('text', { 'font-family': 'Excalifont', 'font-size': 62 }, b.svg);
  probe.textContent = title;
  const w = probe.getComputedTextLength();
  probe.remove();
  const x0 = Math.round(825 - (98 + w) / 2);
  b.at(0);
  b.group({ anim: 'none' }, () => {
    b.ellipse(x0 + 36, 152, 70, 70, { fill, rough: 0.8 });
    b.text(x0 + 36, 165, String(n), { anchor: 'middle', size: 38 });
    b.text(x0 + 98, 174, title, { size: 62 });
    b.line(x0 + 98, 200, x0 + 98 + w, 200, { stroke: ink, sw: 3.2, rough: 0.7, bow: 0.4 });
  });
}

/* ---------- reveal animations ---------- */
const easeOut = t => 1 - Math.pow(1 - t, 3);
const spansOf = g => [...g.querySelectorAll('tspan')];

function stopUnit(g) {
  (g._timers || []).forEach(clearTimeout); g._timers = [];
  if (g._raf) cancelAnimationFrame(g._raf);
  g.getAnimations({ subtree: true }).forEach(a => a.cancel());
  spansOf(g).forEach(ts => { ts.textContent = ts._full; });
  g.querySelectorAll('path').forEach(p => { p.style.strokeDasharray = ''; });
  g.querySelectorAll('rect.bar').forEach(r => r.setAttribute('width', r._w));
}
function showNow(g) { stopUnit(g); g.style.opacity = 1; g._state = 'shown'; }
function hideNow(g) { stopUnit(g); g.style.opacity = 0; g._state = 'hidden'; }

function playUnit(g, delay) {
  stopUnit(g);
  g._state = 'anim';
  const after = (ms, fn) => g._timers.push(setTimeout(fn, ms));
  const anim = g._anim;
  g.style.opacity = 0;

  if (anim === 'none') { g.style.opacity = 1; g._state = 'shown'; return; }
  if (anim === 'fade') {
    g.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 420, delay, fill: 'both', easing: 'ease-out' });
  } else if (anim === 'pop') {
    g.style.transformBox = 'fill-box'; g.style.transformOrigin = 'center';
    g.animate([
      { opacity: 0, transform: 'scale(.55)' },
      { opacity: 1, transform: 'scale(1.07)', offset: 0.65 },
      { opacity: 1, transform: 'scale(1)' },
    ], { duration: 420, delay, fill: 'both', easing: 'ease-out' });
  } else {
    // draw / type / grow
    after(delay, () => { g.style.opacity = 1; });
    if (anim !== 'type') {
      g.querySelectorAll('path').forEach(p => {
        const stroked = p.getAttribute('stroke') && p.getAttribute('stroke') !== 'none' && (!p.getAttribute('fill') || p.getAttribute('fill') === 'none');
        if (stroked && !p.getAttribute('stroke-dasharray')) {
          const L = p.getTotalLength();
          if (!L) return;
          p.style.strokeDasharray = `${L} ${L}`;
          p.animate([{ strokeDashoffset: L }, { strokeDashoffset: 0 }], { duration: Math.max(220, Math.min(620, L * 0.7)), delay, fill: 'both', easing: 'ease-in-out' });
        } else {
          p.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 360, delay: delay + 160, fill: 'both' });
        }
      });
    }
    const bars = [...g.querySelectorAll('rect.bar')];
    if (bars.length) {
      bars.forEach(r => r.setAttribute('width', r._from));
      after(delay, () => {
        const t0 = performance.now();
        const tick = now => {
          const u = Math.min(1, (now - t0) / 700), e = easeOut(u);
          bars.forEach(r => r.setAttribute('width', r._from + (r._w - r._from) * e));
          if (u < 1) g._raf = requestAnimationFrame(tick);
        };
        g._raf = requestAnimationFrame(tick);
      });
    }
    const spans = spansOf(g);
    if (spans.length) {
      const total = spans.reduce((n, ts) => n + ts._full.length, 0);
      const per = Math.min(26, 680 / Math.max(1, total));
      let t = delay + (anim === 'type' ? 0 : 200);
      spans.forEach(ts => {
        ts.textContent = '';
        for (let j = 1; j <= ts._full.length; j++) { const s = ts._full.slice(0, j); after(t, () => { ts.textContent = s; }); t += per; }
      });
    }
  }
  after(delay + 1500, () => { if (g._state === 'anim') g._state = 'shown'; });
}

function applyPart(part, step, animate) {
  const queue = [];
  for (const g of part.units) {
    const visible = step >= g._s && step < g._until;
    if (!visible) { if (g._state !== 'hidden') hideNow(g); continue; }
    if (animate && g._s === step && g._state === 'hidden') queue.push(g);
    else if (g._state === 'hidden') showNow(g);
  }
  queue.forEach((g, i) => playUnit(g, g._delay ?? i * 130));
}

/* ---------- deck: world, camera, navigation ---------- */
function mountDom(nParts) {
  document.body.classList.add('board');
  document.body.insertAdjacentHTML('afterbegin', `
<div id="viewport">
  <div id="stage">
    <div id="world"></div>
    <div id="guides"><div class="edge"></div><div class="cam">camera</div></div>
    <div id="hud"></div>
  </div>
</div>
<div id="demo-nav"><span>press → or tap to step through</span><button type="button" data-go="prev" aria-label="Back">‹</button><button type="button" data-go="next" aria-label="Next">›</button></div>
<div id="help">
  <div><b>→ space</b> next step</div>
  <div><b>←</b> back one step</div>
  <div><b>B</b> board / back into part</div>
  <div><b>1–${nParts}</b> jump to a part</div>
  <div><b>0</b> board</div>
  <div><b>F</b> full screen</div>
  <div><b>P</b> presenter notes window</div>
  <div><b>H</b> show or hide the step counter</div>
  <div><b>G</b> camera-box guide</div>
  <div><b>R</b> restart from the board</div>
  <div><b>?</b> this help</div>
</div>
<div id="presenter">
  <div id="p-top"><span id="p-where"></span><span id="p-time">0:00</span></div>
  <div id="p-cue">Waiting for the deck window…</div>
  <div id="p-next-label">next</div>
  <div id="p-next"></div>
  <div id="p-keys">→ next · ← back · B board · T reset timer · keys here drive the deck</div>
</div>`);
}

function runPresenter() {
  document.body.className = 'presenter';
  const $ = id => document.getElementById(id);
  let t0 = Date.now();
  setInterval(() => { const s = Math.floor((Date.now() - t0) / 1000); $('p-time').textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; }, 500);
  addEventListener('message', e => {
    if (e.data?.type !== 'state') return;
    $('p-where').textContent = e.data.where; $('p-cue').textContent = e.data.cue; $('p-next').textContent = e.data.next;
  });
  addEventListener('keydown', e => {
    if (e.key.toLowerCase() === 't') { t0 = Date.now(); return; }
    if (e.metaKey || e.ctrlKey) return;
    e.preventDefault();
    window.opener?.postMessage({ type: 'key', key: e.key }, '*');
  });
  window.opener?.postMessage({ type: 'hello' }, '*');
}

async function startDeck({ board: BOARD, parts: PARTS }) {
  document.title = BOARD.title;
  mountDom(PARTS.length);
  if (location.hash === '#presenter') return runPresenter();

  const params = new URLSearchParams(location.search);
  if (params.has('demo')) document.body.classList.add('demo');
  const storeKey = 'sketch-deck:' + location.pathname;

  await Promise.all([document.fonts.load('40px Excalifont'), document.fonts.load('30px "Comic Shanns"')]);

  const GAP = 160, COLS = 3, TOP = 700;
  const ROWS = Math.ceil(PARTS.length / COLS);
  const W = COLS * 1920 + (COLS - 1) * GAP;
  const H = TOP + ROWS * 1080 + (ROWS - 1) * GAP;
  const SB = Math.min(1500 / W, 960 / H);
  const BOARD_CAM = { s: SB, x: W / 2, y: H / 2 };

  const stage = document.getElementById('stage');
  const world = document.getElementById('world');
  const hud = document.getElementById('hud');
  const state = { mode: 'board', cur: -1, step: 0, seen: new Set() };
  let cam = { ...BOARD_CAM }, camRaf = 0, presenterWin = null;

  const partPos = k => ({ x: (k % COLS) * (1920 + GAP), y: TOP + Math.floor(k / COLS) * (1080 + GAP) });
  const partCam = k => { const p = partPos(k); return { s: 1, x: p.x + 960, y: p.y + 540 }; };
  const setCam = c => { cam = c; world.style.transform = `translate(${960 - c.s * c.x}px, ${540 - c.s * c.y}px) scale(${c.s})`; };
  function flyTo(to, dur = 1050) {
    cancelAnimationFrame(camRaf);
    const from = { ...cam }, t0 = performance.now();
    const ease = t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    const tick = now => {
      const u = Math.min(1, (now - t0) / dur), e = ease(u);
      setCam({ s: from.s * Math.pow(to.s / from.s, e), x: from.x + (to.x - from.x) * e, y: from.y + (to.y - from.y) * e });
      if (u < 1) camRaf = requestAnimationFrame(tick);
    };
    camRaf = requestAnimationFrame(tick);
  }
  const fit = () => { stage.style.transform = `scale(${Math.min(innerWidth / 1920, innerHeight / 1080)})`; };
  fit(); addEventListener('resize', fit);

  // board title band
  const bsvg = mk('svg', { id: 'board-layer', width: W, height: H, viewBox: `0 0 ${W} ${H}` }, world);
  const bb = new Builder(bsvg, 9000);
  bb.text(W / 2, 420, BOARD.title, { anchor: 'middle', size: 210, anim: 'none' });
  if (BOARD.subtitle) bb.text(W / 2, 580, BOARD.subtitle, { anchor: 'middle', size: 100, color: GRAY, anim: 'none' });
  fixAnchors(bsvg);

  // parts
  PARTS.forEach((p, k) => {
    const pos = partPos(k);
    p.el = document.createElement('div');
    p.el.className = 'slide unseen';
    p.el.style.left = pos.x + 'px'; p.el.style.top = pos.y + 'px';
    world.appendChild(p.el);
    const svg = mk('svg', { width: 1920, height: 1080, viewBox: '0 0 1920 1080' }, p.el);
    const b = new Builder(svg, (k + 1) * 1000);
    header(b, k + 1, p.title, p.color);
    p.build(b);
    fixAnchors(svg);
    p.units = b.units;
    p.max = p.max ?? Math.max(0, ...p.units.map(u => u._s));
  });

  function render() {
    document.body.classList.toggle('board', state.mode === 'board');
    document.body.classList.toggle('card', state.mode === 'card');
    PARTS.forEach((p, k) => p.el.classList.toggle('unseen', !state.seen.has(k)));
    hud.textContent = state.mode === 'card'
      ? `part ${state.cur + 1} · step ${state.step}/${PARTS[state.cur].max}`
      : `board · ${state.seen.size}/${PARTS.length} revealed`;
    try { sessionStorage.setItem(storeKey, JSON.stringify({ mode: state.mode, cur: state.cur, step: state.step, seen: [...state.seen] })); } catch (e) {}
    postState();
  }
  function enterPart(k, step, fly = true) {
    state.mode = 'card'; state.cur = k; state.step = step; state.seen.add(k);
    PARTS.forEach((p, i) => { if (i !== k) applyPart(p, p.max, false); });
    applyPart(PARTS[k], step, false);
    fly ? flyTo(partCam(k)) : setCam(partCam(k));
    render();
  }
  function toBoard(fly = true) {
    state.mode = 'board';
    PARTS.forEach(p => applyPart(p, p.max, false));
    fly ? flyTo(BOARD_CAM) : setCam(BOARD_CAM);
    render();
  }
  function next() {
    if (state.mode === 'card') {
      const p = PARTS[state.cur];
      if (state.step < p.max) { state.step++; applyPart(p, state.step, true); render(); }
      else toBoard();
    } else if (state.cur + 1 < PARTS.length) enterPart(state.cur + 1, 0);
  }
  function prev() {
    if (state.mode === 'card') {
      if (state.step > 0) { state.step--; applyPart(PARTS[state.cur], state.step, false); render(); }
      else { state.seen.delete(state.cur); state.cur--; toBoard(); }
    } else if (state.cur >= 0) enterPart(state.cur, PARTS[state.cur].max);
  }
  function restart() { state.seen.clear(); state.cur = -1; state.step = 0; toBoard(); }

  function handleKey(key) {
    const k = key.length === 1 ? key.toLowerCase() : key;
    if (['ArrowRight', 'ArrowDown', 'PageDown', ' ', 'Enter'].includes(k)) next();
    else if (['ArrowLeft', 'ArrowUp', 'PageUp', 'Backspace'].includes(k)) prev();
    else if (k === 'b') state.mode === 'card' ? toBoard() : enterPart(Math.max(0, state.cur), state.cur >= 0 ? PARTS[state.cur].max : 0);
    else if (k === '0') toBoard();
    else if (/^[1-9]$/.test(k) && +k <= PARTS.length) enterPart(+k - 1, 0);
    else if (k === 'f') document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
    else if (k === 'h') document.body.classList.toggle('showhud');
    else if (k === 'g') document.body.classList.toggle('guides');
    else if (k === '?') document.body.classList.toggle('help');
    else if (k === 'r') restart();
    else if (k === 'p') openPresenter();
    else return false;
    return true;
  }

  // presenter window: notes on a second screen, keys forwarded back here
  function cueFor() {
    if (state.mode === 'card') {
      const p = PARTS[state.cur], notes = p.notes || [];
      return {
        where: `part ${state.cur + 1} · ${p.title} · step ${state.step}/${p.max}`,
        cue: notes[state.step] ?? '',
        next: state.step < p.max ? (notes[state.step + 1] ?? '') : `back to the board, then: ${(BOARD.notes || [])[state.cur + 1] ?? ''}`,
      };
    }
    const k = state.cur + 1;
    return {
      where: `board · ${state.seen.size}/${PARTS.length} revealed`,
      cue: (BOARD.notes || [])[k] ?? '',
      next: k < PARTS.length ? `part ${k + 1}: ${PARTS[k].title}. ${(PARTS[k].notes || [])[0] ?? ''}` : 'end',
    };
  }
  function postState() { if (presenterWin && !presenterWin.closed) presenterWin.postMessage({ type: 'state', ...cueFor() }, '*'); }
  function openPresenter() { presenterWin = window.open(location.href.split('#')[0] + '#presenter', 'deck-presenter', 'width=1000,height=640'); }

  // restore position after a reload
  let saved = null;
  try { saved = JSON.parse(sessionStorage.getItem(storeKey) || 'null'); } catch (e) {}
  if (saved && saved.cur < PARTS.length) {
    state.seen = new Set((saved.seen || []).filter(k => k < PARTS.length)); state.cur = saved.cur;
    saved.mode === 'card' && saved.cur >= 0 ? enterPart(saved.cur, Math.min(saved.step, PARTS[saved.cur].max), false) : toBoard(false);
  } else toBoard(false);

  addEventListener('keydown', e => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (handleKey(e.key)) e.preventDefault();
  });
  addEventListener('message', e => {
    if (e.data?.type === 'hello') { presenterWin = e.source; postState(); }
    else if (e.data?.type === 'key') handleKey(e.data.key);
  });
  document.getElementById('demo-nav').addEventListener('click', e => {
    const go = e.target.closest('button')?.dataset.go;
    if (go === 'next') next(); else if (go === 'prev') prev();
  });
  // touch: tap the right two-thirds to go forward, the left third to go back
  stage.addEventListener('pointerup', e => {
    if (e.pointerType !== 'touch') return;
    e.clientX < innerWidth / 3 ? prev() : next();
  });
  let idle;
  addEventListener('mousemove', () => {
    document.body.classList.remove('idle');
    clearTimeout(idle); idle = setTimeout(() => document.body.classList.add('idle'), 2500);
  });

  // handle for scripts/shots.mjs and the console
  window.deck = {
    parts: PARTS, state, next, prev, restart,
    enter: (k, step = 0, fly = false) => enterPart(k, step === 'max' ? PARTS[k].max : step, fly),
    board: (fly = false) => toBoard(fly),
    seeAll: () => { PARTS.forEach((_, k) => state.seen.add(k)); state.cur = PARTS.length - 1; toBoard(false); },
    ready: true,
  };
}
