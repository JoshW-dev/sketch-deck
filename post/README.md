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

## Also part of a release

- **Thumbnails:** `videos/<slug>/thumbnail.html` with `npm run thumb -- <slug> a b`. Use drawings and big text only, no face. Copy the PNGs into the release folder before running `finish`, so the review page shows them.
- **`youtube.md` in the release folder:**
  - Title: five options, with one recommended.
  - Description in Josh's voice: a hook, what the video shows, chapters, a short bio, links to joshwade.site and this repo, a question for the comments.
  - Tags and a pinned comment.
  - Upload steps: subtitles "With timing", category Education, not made for kids, altered content No, a Subscribe end screen.
- **Listen check:** someone has to hear the voice before upload. The scripts check the numbers, but only a person can say it sounds right.
