/* __TITLE__
   Each part: title, color, max (build steps), notes (one cue per step; index 0 is what you say as the part opens), build(b).
   b.at(n) sets the step that the next elements appear on. Keep content left of x 1540 (press G to see the camera box).
   Colors: orange, yellow, green, blue, purple, red, teal. Red marks the problem, green marks the fix. */

const BOARD = {
  title: '__TITLE__',
  subtitle: 'one line on what the viewer gets',
  // notes[i] = what you say on the board before part i; the last entry is the outro
  notes: [
    'Intro: the hook, then what this video covers.',
    'Outro and call to action.',
  ],
};

const PARTS = [
  {
    title: 'The first idea', color: 'orange', max: 3,
    notes: [
      'What you say as this part opens.',
      'Step 1: the setup.',
      'Step 2: the problem.',
      'Step 3: the takeaway.',
    ],
    build(b) {
      b.at(1);
      b.group(() => { b.rect(130, 340, 300, 120, { fill: '#fff' }); b.text(280, 412, 'Before', { anchor: 'middle', size: 40 }); });
      b.arrow(450, 400, 640, 400);
      b.group(() => { b.rect(660, 340, 300, 120, { fill: PAL.blue[1] }); b.text(810, 412, 'After', { anchor: 'middle', size: 40 }); });

      b.at(2);
      b.text(130, 560, 'the problem, in red', { size: 36, color: RED });
      b.tag(660, 520, 'a labelled detail');

      b.at(3);
      b.callout(130, 820, 1000, 90, 'One line the viewer should remember.');
    },
  },
];

startDeck({ board: BOARD, parts: PARTS });
