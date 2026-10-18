# Post-production

These scripts take a Take recording of a sketch-deck talk and produce everything a YouTube upload needs: a cleaned voice, a tighter edit, a 16:9 1440p file, captions, chapter points and a review page. The first video (AI bottlenecks, October 2026) went through these steps by hand, and the scripts reproduce that result.

## Run it

```bash
post/setup.sh                                                    # once per Mac
post/make.sh prep "~/Movies/Take/Recording ….take" "02 my-topic" "names, jargon"
# read the review list it prints, add hand cuts to work/edl.json "manual"
post/make.sh finish "02 my-topic" "My topic"
open ~/Movies/"Josh Wade AI"/"02 my-topic"/review.html
```

`prep` takes about 6 minutes for an 8-minute talk and `finish` takes about 1 minute. Output goes to `~/Movies/Josh Wade AI/<NN slug>/`: `<Title> (final).mp4`, `.srt` and `review.html`, with intermediate files in `work/`.

## What each step does

1. **export.py**: Take exports at 1440p from a copy of the bundle whose media files are symlinks, so your project is never changed. The deck stage is 16:9 and Take's frame is wider, so the script moves the camera bubble in by the blank margin, and the render crops to exactly 2560x1440. YouTube shows no black bars, and its encode for 1440p uploads keeps the thin sketch lines sharp.
2. **voice.py**: rebuilds the voice from the raw camera mic in four stages.
   - Take's Clean voice is skipped. Its compressor lifts the room echo, with an echo score (SRMR) of 3.83 against 5.39 for the raw mic.
   - MelBand-Roformer dereverb (`audio-separator`, mono anvuew model).
   - Sidon restoration (`speech restore`), which also fixes the thin laptop-mic tone.
   - A light master to -14 LUFS and -1.5 dBTP.
   - Sidon runs on chunks shorter than its 10 s window. On a whole file it drops about 20 ms per window and drifts out of sync.
3. **transcribe.py**: produces two Whisper passes.
   - `words.json` is the clean transcript, used for captions.
   - `words-disfluent.json` keeps "um" and "uh". It's transcribed in 20 to 28 s chunks, because Whisper only uses the filler prompt for its first window.
4. **cuts.py**: two kinds of cut are automatic.
   - **"um" and "uh":** only when it stands alone as its own sound and a transcription of just that piece confirms it. Whisper's word times run up to 200 ms late, so cuts made from them clip the next word.
   - **Pauses over 1 s:** the still middle is trimmed. It keeps 0.35 s after the last word and 0.25 s before the next, and it only cuts while the slide isn't animating.
   - It also lists, but doesn't cut, long silences (usually a restart), phrases said twice within 4 s, and stutters.
5. **Your judgment**: read the transcript around each listed item and pick the take that stays. Add each cut to `"manual"` in `work/edl.json` as `{"start": s, "end": e, "kind": "double take", "label": "..."}`. Rough times are fine, because render.py moves each edge to the quietest 10 ms within 80 ms.
6. **render.py**: one encode from Take's export plus the voice, applying every cut.
   - Video and audio are joined separately, which keeps sound sync exact. A joint concat drifted 31 ms.
   - Picture stays within half a frame (17 ms) of the sound at every cut.
   - It writes the `.srt` and prints the measured sync, loudness and chapter points. A chapter point is where the deck leaves the board for a part.
7. **review.py**: writes `review.html` with the raw mic and the final voice on the same 30 s, the final video with a button for every cut, and the thumbnails.
8. **shorts.py**: vertical shorts from the finished video, see "Shorts" below.

## Shorts

`post/make.sh shorts "02 my-topic"` turns the finished video into vertical shorts (1080x1920): the slide on top, the camera in the bottom third, a hook line that plays first, captions, and a card with the hook text that stays up the whole time. Run `finish` first, because it writes `work/keep.json` and `work/final-words.json`.

1. The first run writes `work/shorts-transcript.txt`, one sentence per line with its time in the final video.
2. Pick the shorts into `work/shorts.json` (format in the header of `shorts.py`). Times are final-video times, the same as YouTube's.
3. Run it again. It writes `shorts/<n> <slug>.mp4`, a contact sheet per short and `shorts.md`. Render one with `make.sh shorts "02 my-topic" 2`. Each takes about 10 to 20 s.
4. Look at the contact sheets, then watch the files. The printout gives length, loudness and sync against the camera's own mic, which should stay within about 20 ms.

How to pick (the hook matters most, because it decides whether anyone keeps watching):

- **Body:** one whole idea with its payoff, 30 s to 3 min. Start on a sentence a stranger can follow with no context, without "so", "and" or "like I said". End on the payoff line. A body can be several spans when a tangent sits in the middle.
- **Hook:** a 2 to 4 s line, usually lifted from later in the body, that plays before the body starts. It has to work cold and do one of five things: break a pattern, make a bold claim, open a question the body answers, speak to the viewer's situation, or give a surprising number. A hook that repeats in the body is fine, because the body pays it off. To drop a filler word inside the hook, give it as a list of spans. An `=` before a time (`"=5:06.45"`) keeps that edge exactly where it is, for when the silence search would reach into the dropped word.
- **Card:** up to about 12 words that state the video's main idea for the viewer's business, with `*stars*` around the words to draw in orange. Keep the example (the lemonade stand, the plant) in the body. On video 01 the lemonade short's card is "Why most businesses use AI on the wrong problem", and the $100 mixer stays in what Josh says. Only claim what the short supports. Highstyle's most-liked complaints were titles that didn't match the clip.
- **Frame 0 is the cover** in the Shorts feed, so the hook should start on a slide that already shows something.

What the script does: it maps each span from the final video back to Take's `screen.mov` and `camera.mov` through `keep.json` and Take's cuts. It moves each edge into the quietest 10 ms nearby, searching further back at a start and further on at an end, since Whisper's times run late. It crops the slide to everything drawn during the short (never right of x 1560 on the deck canvas) and finds the face with OpenCV for the camera crop. Set `"face": [cx, cy, width]` in `shorts.json` to place it by hand. The layout is composed in RGB, because overlaying the screen's YUV on a YUV page shifted the slide's white by 3 levels and drew a box around it.

## Also part of a release

- **Thumbnails:** `videos/<slug>/thumbnail.html` with `npm run thumb -- <slug> a b`. Use drawings and big text only, no face. Copy the PNGs into the release folder before running `finish`, so the review page shows them.
- **`youtube.md` in the release folder:**
  - Title: five options, with one recommended.
  - Description in Josh's voice: a hook, what the video shows, chapters, a short bio, links to joshwade.site and this repo, a question for the comments.
  - Tags and a pinned comment.
  - Upload steps: subtitles "With timing", category Education, not made for kids, altered content No, a Subscribe end screen.
- **Listen check:** someone has to hear the voice before upload. The scripts check the numbers, but only a person can say it sounds right.
