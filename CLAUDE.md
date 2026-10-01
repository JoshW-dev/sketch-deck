# sketch-deck

Hand-drawn animated decks for talking-head videos. The engine is `engine/deck.js`. Each video is `videos/<slug>/` with `content.js` (the parts) and `outline.md` (the talk).

## Making a video

1. `npm run new -- <slug> "Title"` copies `templates/video/`.
2. Fill `outline.md` first: the one-sentence point, then 4 to 6 parts of about 50 seconds each.
3. Write the parts in `content.js`. Preview by opening `videos/<slug>/index.html` in Chrome, or `npm run serve` and http://localhost:8812/videos/<slug>/.
4. Run `npm run shots -- <slug>` and look at every `part-N.png` for overlaps before calling a deck done.

## Layout rules

- Canvas is 1920x1080. The engine draws the numbered title (y 110 to 200).
- Content goes in x 110 to 1540, y 270 to 980. Nothing right of x 1560: the camera box sits at x 1600 to 1900, y 290 to 790 (press G to see it).
- One idea per part, about 5 steps. The last step is the takeaway, often `b.callout(...)`.
- Each step adds one thing that matches one sentence of narration. Put that sentence's cue in `notes[step]`; `notes[0]` is what the speaker says as the part opens.
- Sizes: labels 30 to 40, small context notes 26 to 28 in `GRAY`, headline numbers 44. Use `mono: true` for numbers, units and code.
- Color carries meaning: `RED` is the problem or the bottleneck, `GREEN` is the fix or the gain, `GRAY` is context. Use pastel fills (`PAL.<color>[1]`) only on elements that mean something.
- Show a change with `until` on the old element and a new element at the next step (`from` on a bar animates the resize). Strike an old number with a red line and type the new one in green.
- Text width estimates: Excalifont about 0.5 x size per character, Comic Shanns about 0.6 x size. Check that no text crosses a shape.
- Sequence items inside a step with `delay` in ms. Give a draw about 500 ms and a bar about 700 ms before the label that depends on it.

## Engine

- Builder methods: `rect`, `ellipse`, `line`, `arrow`, `curveArrow`, `lpath`, `poly`, `path`, `text`, `bar`, `check`, `cross`, `tag`, `bubble`, `callout`, `doc`, `clock`, `person`, `sparkle`, and `group(fn)` for a single reveal unit.
- Drawings used by one video go in that video's `content.js` as plain functions that take `b` (see `juiceBox` and `machineIcon` in `videos/ai-bottleneck`). Change the engine only for something every video needs.
- `window.deck` exposes `enter(k, 'max')`, `board()`, `seeAll()`, `next()` and `prev()` for scripts and the console. Check the console for errors after any change.

## Writing

- Cues in `notes` are short and spoken, in the speaker's own words.
- No em dashes in slide text, cues or docs.
