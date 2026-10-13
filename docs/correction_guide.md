# Correcting Reference Transcripts

Reference transcripts are episodes corrected by ear. They are used to measure transcription accuracy (`evaluation/evaluate.py`) and later to train and test speaker identification. Correcting a Whisper draft is much faster than typing an episode from scratch, about 30-60 minutes for an 8-minute episode.

## Workflow
1. Make a draft from the transcriber output:
   ```
   python transcriber/json_to_vtt.py s1ep1-Rakija
   ```
   It is saved to `data/samples/drafts/s1ep1-Rakija.vtt`, one cue (line) per sentence.
2. Open it in [Subtitle Edit](https://www.nikse.dk/subtitleedit) (free, Windows): *File → Open* the `.vtt`, then *Video → Open video file* and pick the episode audio from `data/samples/audio/`. Click *Add waveform* to see the audio.
3. Go through every cue: listen, correct the text, add the speaker (see below). Use slower playback for fast dialogue.
4. Save as WebVTT to `data/samples/correct_samples/s1ep1-Rakija.vtt` (same name as the audio). A `.vtt` reference is used instead of an older `.txt` with the same name.
5. Set `reference_checked` to `True` for the episode in `data/samples/samples_dataset.csv`. Only checked references are scored.

## Draft markers
- `word(?)`: Whisper was unsure about this word, listen closely.
- `[CHECK: no text here, missed speech?]`: a stretch of 10+ seconds without text. Usually the intro, music or laughter, then delete the cue. If someone speaks there, write the dialogue and fix the cue times.

Remove all markers when done. `evaluate.py` warns about references that still contain them.

**Listen to every line, even when it looks right.** Plausible-looking mistakes are easy to accept when reading a draft, and they make the reference favour the model that wrote it.

## What to write
- **Exactly what is said**, not what should have been said. Keep dialect, slang, grammar mistakes and unfinished words (`oćeš`, `đe`, `bre`, `kao fol`).
- **Latin script**, with č, ć, š, ž, đ.
- **Numbers in digits** (`5`, `2015`, `200 dinara`), as Whisper writes them, so formatting does not count as an error.
- **Interjections that are words**: `aha`, `e`, `ej`, `ma`, `pa`, `a?`. Skip pure hesitation sounds (`hm`, `ee...`).
- **Repetitions as said**: `sve ok, sve ok`.
- **Punctuation** as it helps reading. It is ignored in scoring.
- **Non-speech** in square brackets, optional: `[smeh]`, `[muzika]`, `[aplauz]`. Anything in `[...]` is ignored in scoring.
- **Unclear speech**: `[nerazgovetno]`. Use it only when you really can't make out the words after a few listens.
- **Songs and singing**: write the words if they are clear, otherwise `[pesma]`.

## Speakers
Start each cue with the speaker in a WebVTT voice tag:
```
00:01:15.460 --> 00:01:16.940
<v Čvarkov>Ma, sve ok, sve ok.
```
- Main characters: `Čvarkov`, `Torbica`, `Boškić`.
- Other characters: their name if known, the same spelling every time.
- `Other` for someone without a name (waiter, voice on the phone), `Unknown` when you can't tell who speaks.
- **One speaker per cue.** If the speaker changes inside a cue, split it (*right click → Split*, or put the cursor where the split goes and press the split shortcut) and fix the times so each cue covers only its speaker.
- Overlapping speech: one cue per speaker, the times may overlap.

## Times
Times come from Whisper and are usually close. Fix them only when they are off by more than about a second, or when you split a cue between speakers. They don't need to be exact.

## Other languages
Some lines are in German, Hungarian, English and other languages. For now, write what is said in that language's Latin spelling. Whisper often translates such lines into Serbian, so check them by ear. Optionally mark them with a language span, it is kept in scoring:
```
<v Torbica><lang de>Guten Tag, wie geht's?</lang>
```

## Before marking an episode as checked
- [ ] Every cue was listened to.
- [ ] No `(?)` or `[CHECK` markers left.
- [ ] Every cue has a `<v Speaker>` tag.
- [ ] Saved as `.vtt` in `data/samples/correct_samples/` with the episode's file name.
