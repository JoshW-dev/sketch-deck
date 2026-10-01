/* Put AI on the bottleneck: a 5-minute talk.
   Each part: title, color, max (build steps), notes (one cue per step; index 0 is what you say as the part opens), build(b).
   b.at(n) sets the step that the next elements appear on. Keep content left of x 1540. */

const BOARD = {
  title: 'Put AI on the bottleneck',
  subtitle: 'lemonade, juice boxes, and your business',
  // notes[i] = cue while the board is up and part i is next; last = outro
  notes: [
    'Intro. Most AI rollouts save time nobody needed saved. Today: where AI actually pays. A lemonade stand, a juice box plant, then your business.',
    'Let me make this concrete.',
    'So what is the stand actually short on?',
    'I learned this on factory floors.',
    'Now map it onto a real business.',
    'So what do you do with this on Monday?',
    'Outro and CTA.',
  ],
};

const PARTS = [
  {
    title: 'AI for its own sake', color: 'orange', max: 5,
    notes: [
      'Owners and consultants add AI to a business. Here is the core problem.',
      'Picture any business as a line: marketing, sales, delivery, admin.',
      'Most AI lands back here. Meeting notes, invoice OCR, drafts, inbox.',
      'It saves real hours. It feels productive.',
      'But revenue does not move.',
      'AI needs a job. The job is whatever limits output. That is the bottleneck.',
    ],
    build(b) {
      b.at(1);
      b.text(130, 318, 'your business', { size: 28, color: GRAY, anim: 'fade' });
      const xs = [130, 470, 810, 1150], names = ['Marketing', 'Sales', 'Delivery', 'Admin'];
      xs.forEach((x, i) => {
        b.group(() => { b.rect(x, 340, 250, 110, { fill: '#fff' }); b.text(x + 125, 406, names[i], { anchor: 'middle', size: 36 }); });
        if (i < 3) b.arrow(x + 262, 395, xs[i + 1] - 12, 395);
      });

      b.at(2);
      b.text(810, 508, 'where AI usually lands', { size: 26, color: GRAY, anim: 'fade' });
      b.tag(810, 528, 'meeting notes');
      b.tag(810, 588, 'report drafts');
      b.tag(1150, 528, 'invoice OCR');
      b.tag(1150, 588, 'inbox sorting');

      b.at(3);
      b.group(() => { b.clock(836, 692, 22); b.text(872, 704, 'saves 6 hrs/week', { size: 36, color: GREEN }); });

      b.at(4);
      b.group(() => {
        b.lpath([[130, 540], [130, 760], [600, 760]], { sw: 2 });
        b.text(146, 568, 'revenue', { size: 26, color: GRAY });
        b.lpath([[150, 700], [230, 695], [310, 703], [390, 697], [470, 702], [570, 699]], { stroke: PAL.blue[0], sw: 3, rough: 1.2 });
        b.text(470, 790, 'weeks', { size: 22, color: GRAY });
      });
      b.text(130, 830, 'revenue: flat', { size: 36, color: RED, delay: 700 });

      b.at(5);
      b.group(() => {
        b.rect(400, 870, 820, 88, { fill: PAL.yellow[1], r: 16 });
        b.text(810, 927, 'Ask first: what limits our output?', { anchor: 'middle', size: 40 });
      });
    },
  },

  {
    title: 'The $100 mixer', color: 'yellow', max: 5,
    notes: [
      'Say I start a lemonade stand.',
      'Lemons, sugar, water. I mix one batch each morning and sell from the stand.',
      'A dollar a glass, about 20 glasses a day. Mixing takes 20 minutes.',
      'Someone offers me a state-of-the-art mixer for $100. Should I buy it?',
      'It is faster. Mixing goes from 20 minutes to 2.',
      'But I still sell 20 glasses. Extra revenue: zero.',
    ],
    build(b) {
      b.at(1);
      b.group(() => {
        // awning with scallops
        let d = 'M185,300 H495 L540,370';
        for (let i = 0; i < 8; i++) { const x = 540 - i * 50; d += ` Q${x - 25},398 ${x - 50},370`; }
        b.path(d + ' Z', { fill: PAL.yellow[1] });
        [0.25, 0.5, 0.75].forEach(t => b.line(185 + 310 * t, 302, 140 + 400 * t, 368, { stroke: PAL.yellow[0], sw: 1.6 }));
        b.line(175, 378, 175, 560, { sw: 3 });
        b.line(505, 378, 505, 560, { sw: 3 });
        b.rect(150, 560, 380, 170, { fill: '#fff', r: 6 });
        b.text(340, 640, 'LEMONADE', { anchor: 'middle', size: 46 });
        b.text(340, 692, '$1 a cup', { anchor: 'middle', size: 30, color: GRAY });
        // pitcher, cups, lemons
        b.path('M222,468 L296,468 L288,558 L230,558 Z', { fill: '#fff3bf' });
        b.path('M296,484 Q326,500 292,536', { sw: 2.2 });
        [328, 374, 420].forEach(x => b.path(`M${x},516 L${x + 32},516 L${x + 28},558 L${x + 4},558 Z`, { fill: '#fff' }));
        b.ellipse(478, 542, 40, 30, { fill: '#ffe066' });
        b.ellipse(462, 517, 38, 28, { fill: '#ffe066' });
      });
      b.text(150, 790, 'one batch each morning', { size: 28, color: GRAY, anim: 'fade', delay: 900 });

      b.at(2);
      b.text(680, 340, '20 cups × $1 = $20/day', { mono: true, size: 40 });
      b.text(680, 420, 'mixing time', { size: 28, color: GRAY });
      b.bar(680, 438, 600, 44, { fill: PAL.orange[1], until: 4 });
      b.text(1296, 470, '20 min', { mono: true, size: 26, until: 4, delay: 700 });

      b.at(3);
      b.person(720, 650);
      b.bubble(790, 580, 480, 110, 'State-of-the-art mixer.\nOnly $100.', { size: 30 });
      b.group(() => {
        b.path('M1352,700 L1340,610 L1480,610 L1468,700 Z', { fill: '#fff' });
        b.lpath([[1382, 668], [1410, 648], [1438, 668]], { sw: 2.2 });
        b.rect(1336, 700, 148, 92, { fill: '#e9ecef', r: 10 });
        b.ellipse(1410, 746, 30, 30, { fill: '#fff' });
        b.sparkle(1484, 606, 15);
      });
      b.group({ anim: 'pop', delay: 900 }, () => {
        b.rect(1355, 812, 110, 44, { fill: PAL.red[1], r: 8 });
        b.text(1410, 843, '$100', { anchor: 'middle', mono: true, size: 24 });
      });

      b.at(4);
      b.bar(680, 438, 60, 44, { fill: PAL.green[1], from: 600 });
      b.text(756, 470, '2 min', { mono: true, size: 26, delay: 700 });
      b.text(680, 540, 'saves 18 min/day', { size: 36, color: GREEN, delay: 900 });

      b.at(5);
      b.text(680, 900, 'extra revenue: $0/day', { size: 46, color: RED });
      b.text(680, 950, 'still 20 cups a day', { size: 28, color: GRAY, delay: 700 });
    },
  },

  {
    title: 'The limit is customers', color: 'green', max: 5,
    notes: [
      'Mixing was never my limit.',
      'I can make about 100 cups a day.',
      'I sell 20. Most of my capacity sits idle.',
      'The bottleneck is customers.',
      'So my 30 minutes goes to getting customers. Better corner, bigger sign, regulars.',
      'At 100 cups I batch 5 times a day. Now the mixer saves 90 minutes a day. Now buy it.',
    ],
    build(b) {
      b.at(1);
      b.text(130, 368, 'can make', { size: 32, color: GRAY });
      b.bar(330, 330, 1000, 52, { fill: '#fff' });
      b.text(1346, 366, '100 cups/day', { mono: true, size: 26, delay: 700 });

      b.at(2);
      b.text(130, 478, 'sell', { size: 32, color: GRAY });
      b.bar(330, 440, 200, 52, { fill: PAL.green[1], until: 5 });
      b.text(1346, 476, '20 cups/day', { mono: true, size: 26, until: 5, delay: 500 });
      b.rect(534, 444, 792, 44, { fill: LIGHT, fillStyle: 'hachure', gap: 11, stroke: 'none', r: 0, until: 5, delay: 800 });
      b.text(930, 540, '80 cups of idle capacity', { anchor: 'middle', size: 28, color: GRAY, until: 5, delay: 1000 });

      b.at(3);
      b.ellipse(430, 466, 290, 112, { stroke: RED, sw: 2.6, until: 5 });
      b.text(330, 570, 'bottleneck: customers', { size: 38, color: RED, until: 5, delay: 500 });

      b.at(4);
      b.text(130, 668, 'so the 30 minutes goes to:', { size: 30, color: GRAY });
      const chips = [[130, 'better corner'], [358, 'bigger sign'], [559, 'regulars'], [720, 'word of mouth']];
      chips.forEach(([x, t]) => b.tag(x, 690, t, { spark: false, fill: PAL.green[1] }));

      b.at(5);
      b.bar(330, 440, 1000, 52, { fill: PAL.green[1], from: 200 });
      b.text(1346, 476, '100 cups/day', { mono: true, size: 26, delay: 700 });
      b.text(330, 570, 'bottleneck moves to mixing', { size: 38, color: RED, delay: 900 });
      b.text(130, 830, '5 batches × 20 min = 100 min of mixing a day', { mono: true, size: 30, delay: 1300 });
      b.text(130, 900, 'Now the $100 mixer pays: it saves 90 min a day.', { size: 40, color: GREEN, delay: 1700 });
    },
  },

  {
    title: 'One bottleneck sets the output', color: 'blue', max: 5,
    notes: [
      'Where I learned this: a few years as an operations consultant in US manufacturing plants.',
      'Say a juice box line. Filler, labeler, packer, palletizer.',
      'Every machine has a rate.',
      'Our rule: every line has one bottleneck. Here it is the filler, and it sets the output.',
      'Upgrade the labeler. Output does not change.',
      'Upgrade the filler. Output goes up. Goldratt called this the Theory of Constraints.',
    ],
    build(b) {
      b.at(1);
      b.text(130, 296, 'a juice box line', { size: 28, color: GRAY, anim: 'fade' });
      const xs = [130, 470, 810, 1150], names = ['Filler', 'Labeler', 'Packer', 'Palletizer'];
      b.group(() => {
        b.line(110, 522, 1410, 522, { sw: 2 });
        b.line(110, 546, 1410, 546, { sw: 2 });
        for (let x = 140; x < 1400; x += 70) b.ellipse(x, 534, 14, 14, { sw: 1.3, rough: 0.6 });
      });
      xs.forEach((x, i) => b.group(() => {
        b.rect(x, 340, 240, 150, { fill: '#fff' });
        machineIcon(b, i, x + 120, 395);
        b.text(x + 120, 470, names[i], { anchor: 'middle', size: 32 });
      }));
      [398, 428, 738, 768, 1078, 1108].forEach((x, i) => b.group({ anim: 'pop', delay: 900 + i * 60 }, () => juiceBox(b, x, 486)));

      b.at(2);
      ['600/hr', '900/hr', '1,000/hr', '1,200/hr'].forEach((t, i) => b.text(xs[i] + 120, 600, t, { anchor: 'middle', mono: true, size: 30 }));

      b.at(3);
      b.ellipse(250, 478, 290, 290, { stroke: RED, sw: 2.6 });
      b.text(250, 710, 'bottleneck', { anchor: 'middle', size: 38, color: RED, delay: 500 });
      b.text(820, 760, 'line output:', { size: 34, color: GRAY, delay: 800 });
      b.text(1040, 762, '600/hr', { mono: true, size: 44, until: 5, delay: 1000 });

      b.at(4);
      b.line(526, 590, 654, 590, { stroke: RED, sw: 3 });
      b.text(590, 656, '1,500/hr', { anchor: 'middle', mono: true, size: 30, color: GREEN, delay: 300 });
      b.text(1240, 762, 'no change', { size: 36, color: RED, until: 5, delay: 900 });

      b.at(5);
      b.line(186, 590, 314, 590, { stroke: RED, sw: 3 });
      b.text(250, 656, '800/hr', { anchor: 'middle', mono: true, size: 30, color: GREEN, delay: 300 });
      b.text(1040, 762, '800/hr', { mono: true, size: 44, color: GREEN, delay: 800 });
      b.text(1240, 762, 'up 33%', { size: 36, color: GREEN, delay: 1100 });
      b.text(130, 920, 'Goldratt called this the Theory of Constraints (The Goal, 1984).', { size: 26, color: GRAY, anim: 'fade', delay: 1400 });
    },
  },

  {
    title: 'Most businesses are demand-constrained', color: 'purple', max: 5,
    notes: [
      'Same thing in a business.',
      'Content, leads, sales, delivery, admin.',
      'Typical numbers: 10 leads a month, 2 new clients, room for 8.',
      'For most businesses the filler is demand.',
      'This is where AI usually goes. That is the labeler.',
      'It pays up front: content, outreach, follow-up, the sales funnel.',
    ],
    build(b) {
      b.at(1);
      b.text(130, 300, 'a typical service business', { size: 28, color: GRAY, anim: 'fade' });
      const xs = [130, 420, 710, 1000, 1290], names = ['Content', 'Leads', 'Sales', 'Delivery', 'Admin'];
      xs.forEach((x, i) => {
        b.group(() => { b.rect(x, 330, 220, 110, { fill: '#fff' }); b.text(x + 110, 396, names[i], { anchor: 'middle', size: 34 }); });
        if (i < 4) b.arrow(x + 228, 385, xs[i + 1] - 8, 385, { head: 13 });
      });

      b.at(2);
      ['2 posts/wk', '10/mo', '2 won/mo', 'room for 8/mo'].forEach((t, i) => b.text(xs[i] + 110, 492, t, { anchor: 'middle', mono: true, size: 24 }));

      b.at(3);
      b.ellipse(675, 412, 618, 232, { stroke: RED, sw: 2.6 });
      b.text(675, 588, 'bottleneck: demand', { anchor: 'middle', size: 38, color: RED, delay: 500 });
      b.text(1110, 534, '6 slots open', { anchor: 'middle', size: 26, color: GRAY, delay: 800 });

      b.at(4);
      b.group({ anim: 'fade' }, () => { b.cross(1000, 630, 22); b.text(1036, 652, 'where AI usually goes', { size: 30, color: RED }); });
      const grayTag = { fill: '#f1f3f5', sparkFill: LIGHT };
      b.tag(1000, 676, 'meeting notes', grayTag);
      b.tag(1000, 736, 'report drafts', grayTag);
      b.tag(1290, 676, 'invoice OCR', grayTag);
      b.tag(1290, 736, 'inbox sorting', grayTag);

      b.at(5);
      b.group({ anim: 'fade' }, () => { b.check(130, 628, 26); b.text(170, 652, 'where AI pays', { size: 30, color: GREEN }); });
      const greenTag = { fill: PAL.green[1] };
      b.tag(130, 676, 'more content', greenTag);
      b.tag(130, 736, 'faster outreach', greenTag);
      b.tag(420, 676, 'lead follow-up', greenTag);
      b.tag(420, 736, 'funnel fixes', greenTag);
      b.group({ delay: 1000 }, () => {
        b.rect(360, 860, 900, 86, { fill: PAL.yellow[1], r: 16 });
        b.text(810, 915, 'Same rule as the plant: work on the filler.', { anchor: 'middle', size: 38 });
      });
    },
  },

  {
    title: 'Find your bottleneck first', color: 'red', max: 5,
    notes: [
      'So before you buy the mixer:',
      'Map the line. Every step from stranger to paying customer.',
      'Find the slowest step. The one everything else waits on.',
      'Point AI there, and measure the output it adds.',
      'Fix it and the bottleneck moves. Then go again.',
      'If it is not the bottleneck, it can wait.',
    ],
    build(b) {
      const items = [
        ['Map the line', 'every step from stranger to paying customer'],
        ['Find the slowest step', 'the one everything else waits on'],
        ['Point AI there', 'and measure the output it adds'],
        ['Re-check when it moves', 'fix one bottleneck and the next one shows up'],
      ];
      items.forEach(([t, sub], i) => {
        const y = 340 + i * 125;
        b.at(i + 1);
        b.group(() => {
          b.rect(150, y - 36, 46, 46, { fill: '#fff', r: 8 });
          b.text(226, y, t, { size: 42 });
          b.text(226, y + 42, sub, { size: 27, color: GRAY });
        });
        b.check(158, y - 30, 32, { delay: 700 });
      });

      const ys = [320, 410, 500, 590, 680], nm = ['Content', 'Leads', 'Sales', 'Delivery', 'Admin'];
      b.at(1);
      b.group({ delay: 300 }, () => ys.forEach((y, i) => {
        b.rect(1290, y, 200, 56, { fill: '#fff', r: 10 });
        b.text(1390, y + 38, nm[i], { anchor: 'middle', size: 28 });
        if (i < 4) b.arrow(1390, y + 60, 1390, ys[i + 1] - 4, { head: 10, sw: 1.6 });
      }));
      b.at(2);
      b.ellipse(1390, 438, 272, 98, { stroke: RED, sw: 2.6, delay: 500, until: 4 });
      b.at(3);
      b.tag(1150, 415, 'AI', { delay: 500 });
      b.at(4);
      b.check(1502, 424, 28, { delay: 200 });
      b.ellipse(1390, 528, 272, 98, { stroke: RED, sw: 2.2, dash: [10, 8], delay: 500 });
      b.text(1250, 538, 'then this one', { anchor: 'end', size: 26, color: GRAY, delay: 800 });

      b.at(5);
      b.group(() => {
        b.rect(150, 850, 1000, 90, { fill: PAL.yellow[1], r: 16 });
        b.text(650, 908, "If it isn't the bottleneck, it can wait.", { anchor: 'middle', size: 42 });
      });
    },
  },
];

// drawings used only in this video
function juiceBox(b, x, y) {
  b.rect(x, y, 24, 34, { fill: PAL.orange[1], sw: 1.5, r: 3 });
  b.line(x + 16, y, x + 21, y - 13, { sw: 1.8, rough: 0.4 });
}
function machineIcon(b, i, cx, cy) {
  if (i === 0) {        // filler: nozzle and drop
    b.path(`M${cx - 24},${cy - 26} L${cx + 24},${cy - 26} L${cx + 9},${cy + 4} L${cx - 9},${cy + 4} Z`, { fill: PAL.blue[1] });
    b.path(`M${cx},${cy + 12} Q${cx + 10},${cy + 28} ${cx},${cy + 34} Q${cx - 10},${cy + 28} ${cx},${cy + 12} Z`, { fill: PAL.blue[0], stroke: PAL.blue[0], sw: 1.2, rough: 0.3 });
  } else if (i === 1) { // labeler: tag
    b.path(`M${cx - 32},${cy - 18} H${cx + 16} L${cx + 32},${cy} L${cx + 16},${cy + 18} H${cx - 32} Z`, { fill: PAL.yellow[1] });
    b.ellipse(cx + 14, cy, 9, 9, { sw: 1.5, rough: 0.3 });
  } else if (i === 2) { // packer: open box
    b.rect(cx - 28, cy - 12, 56, 38, { fill: PAL.orange[1], r: 3 });
    b.line(cx - 28, cy - 12, cx - 40, cy - 28, { sw: 1.8 });
    b.line(cx + 28, cy - 12, cx + 40, cy - 28, { sw: 1.8 });
  } else {              // palletizer: stacked boxes
    b.rect(cx - 32, cy + 2, 30, 22, { fill: PAL.orange[1], r: 2 });
    b.rect(cx + 2, cy + 2, 30, 22, { fill: PAL.orange[1], r: 2 });
    b.rect(cx - 15, cy - 22, 30, 22, { fill: PAL.orange[1], r: 2 });
    b.line(cx - 42, cy + 28, cx + 42, cy + 28, { sw: 3 });
  }
}

startDeck({ board: BOARD, parts: PARTS });
