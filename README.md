###### Project is still in progress

## Idea Behind the Project
### Making transcript of every episode for one of the most popular TV shows in the region "Državni Posao" (eng. smth. like "Government Job"). There is no similar project nor dataset out there. 

## Goal
### Possibilities are unlimited, for both analysis and general curiosity. 
#### Do you want to find your favorite joke? 
- Just search through the dataset.
#### Wanna watch all the occurrences of a certain character?
- Again, just search through the dataset
#### Interested in making any data analysis of the show?
- Once more, just go through the dataset.

## Help of the Community
### There is a certain possibility that this "one man" project would be done in 1-2 years.
### This is an open-source project, any help from the community is welcome.

## Methodology
### So far, one of the working steps would be the following:
- Scrape titles and links of each episode from YouTube. (yt-dlp, see "Scraping the Data" below)
- Download audio of each episode. (yt-dlp, see "Downloading Audio" below)
- Transcribe each episode with Whisper large-v3. (faster-whisper, see "Transcribing" below)
- Do all of the above for every episode in one go, deleting audio as it goes. (see "Transcribing All Episodes" below)
- Store episodes and extract valuable data from them into the main dataset.

## Scraping the Data
### The scraper collects episode metadata from the official YouTube channel, no browser needed.
```
pip install -r requirements.txt
python scraper/script.py
```
- Reads season playlists from `data/scraper_data/playlist_input.csv` (add a row there for each new season).
- Writes raw playlist data to `data/scraper_data/playlist_output.csv`.
- Writes parsed data to `data/clean_data/episodes.csv` and `data/clean_data/bonus_content.csv`.
- Also checks the channel for episodes that were uploaded but left out of the season playlists (skip with `--no-channel`).
- Run `python scraper/script.py --help` for all options. If YouTube changes break scraping, update yt-dlp first: `pip install -U yt-dlp`.

## Downloading Audio
### The downloader saves each episode's original YouTube audio (usually Opus in a `.webm` file, about 5 MB per episode) without converting it. Whisper decodes it directly, so converting to MP3 or WAV would only cost time and quality.
```
python downloader/utils.py
python downloader/utils.py --limit 1
python downloader/utils.py --csv data/clean_data/episodes.csv --output-dir audio
```
- Requires [FFmpeg](https://ffmpeg.org/download.html) on your PATH, which Whisper uses to decode the audio.
- Reads episodes from `data/samples/samples_dataset.csv` by default, and saves audio to `data/samples/audio/`.
- The `downloaded` column in the CSV tracks progress: an episode is marked `True` right after its audio is saved, and episodes already marked `True` are skipped on the next run. If the column is missing, it is added.
- Videos that fail to download (private, removed, region-locked) are skipped and stay `False`, so the next run retries them.
- `--limit N` downloads at most N episodes, which is useful for a quick test.
- The transcriber accepts `.webm`, `.m4a`, `.opus`, `.mp3` and `.wav` files.

### Troubleshooting
- `The page needs to be reloaded` or other YouTube errors usually mean yt-dlp is outdated: `pip install -U yt-dlp`.
- yt-dlp may warn that no JavaScript runtime was found. Downloads still work for now, but installing [Deno](https://deno.com/) (`winget install DenoLand.Deno` on Windows) keeps them working when YouTube requires it.

## Transcribing
### `transcriber/utils.py` transcribes audio with [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (Whisper large-v3 by default) and saves one JSON file per episode.
```
pip install -r requirements-transcriber.txt
python transcriber/utils.py
python transcriber/utils.py --model large-v3-turbo --input data/samples/audio/s1ep1-Rakija.wav
```
- Runs on an NVIDIA GPU when available (int8, about 3.5 GB VRAM for large-v3), otherwise on the CPU. The CUDA 12 libraries are installed by `requirements-transcriber.txt`.
- Reads audio from `data/samples/audio/` and saves to `data/samples/fw_<model>/`, so `evaluation/evaluate.py` picks the results up. Files that already have a transcript are skipped.
- Settings chosen against Whisper's loops and invented text: voice activity detection (skips music and silence), no conditioning on previous text, beam search and a Latin-script prompt. Character names as hotwords were tested and left out, they made Whisper skip whole 30-second windows of dialogue.
- After transcription, Cyrillic is converted to Latin and segments that are most likely invented are removed: the leaked prompt, only "Muzika"/🎵, phrases like "Hvala što pratite kanal", and the same text repeated more than twice. Removed segments are kept in `removed_segments` in the JSON.
- Whisper sometimes returns nothing for a whole stretch of dialogue. After each episode, stretches of 5+ seconds without text that contain at least 3 seconds of detected speech are transcribed again on their own. The result is kept only if Whisper is confident, otherwise the stretch stays empty and the VTT draft flags it for checking. Laughter ("Hahaha") is dropped like other non-speech. Each JSON lists the checked stretches in `gaps_checked`, and added segments have `"gap_fill": true`. `--no-gap-fill` turns this off, `--fill-existing` runs it on transcripts made before it existed.
- Each JSON has the full `text`, `segments` with start/end times and word timestamps, the model and settings used, and processing time.
- Keeps Windows awake while running (closing a laptop lid still sleeps). On laptops, make sure the GPU is not power-limited by the manufacturer's power mode, `nvidia-smi -q -d POWER` shows the current limit.

## Transcribing All Episodes
### `pipeline.py` goes through every episode in `data/clean_data/episodes.csv`: downloads its audio, transcribes it, saves the transcript and deletes the audio before the next episode, so only one episode's audio is ever on disk.
```
pip install -r requirements-transcriber.txt
python pipeline.py
python pipeline.py --seasons 1 2
python pipeline.py --limit 10
```
- Safe to stop at any time (Ctrl+C, closing the window, a crash or sleep). Run the same command again and it continues, episodes that already have a transcript are skipped.
- Transcripts are saved to `data/transcripts/fw_large-v3/` in the same JSON format as `transcriber/utils.py`, plus the episode's `metadata` (season, number, name, title, date, URL). About 140 KB per episode, around 350 MB for all of them. The folder is not tracked in git.
- `data/transcripts/progress.csv` tracks every episode: `done`, `download failed` or `transcription failed`, with the error, audio length, processing time and word count. Failed episodes are retried on the next run unless `--skip-failed` is given.
- After 5 failed downloads in a row it stops, that usually means yt-dlp is outdated (`pip install -U yt-dlp`) or YouTube is blocking for a while.
- It waits 5 seconds between episodes to go easy on YouTube (`--sleep`).
- **It takes long**: the show has about 360 hours of audio. On a laptop RTX 3060 limited to 30 W that's around 190 hours of processing, about 8 days running nonstop, faster on a GPU with full power. Running a season or two at a time with `--seasons` works well. It prints an estimate of the time left after each episode.
- Run it in your own terminal, keep the laptop plugged in and the lid open.

## Correcting Reference Transcripts
### Accuracy is measured against episodes corrected by ear. `transcriber/json_to_vtt.py` turns transcriber output into WebVTT drafts that are corrected in [Subtitle Edit](https://www.nikse.dk/subtitleedit), together with speaker labels.
```
python transcriber/json_to_vtt.py
python transcriber/json_to_vtt.py s1ep1-Rakija --min-probability 0.4
```
- Reads `data/samples/fw_large-v3/` and saves drafts to `data/samples/drafts/`, one cue per sentence.
- Words Whisper was unsure about are marked `(?)`, stretches of 10+ seconds without text are marked `[CHECK: ...]`.
- How to correct a draft, write speakers and mark it as checked: [docs/correction_guide.md](docs/correction_guide.md).

## Evaluating Transcription Quality
### `evaluation/evaluate.py` scores model transcripts against hand-corrected references, so different models and settings can be compared with numbers.
```
python evaluation/evaluate.py
python evaluation/evaluate.py --models whisper_small whisper_large --per-file
python evaluation/evaluate.py --show s1ep1-Rakija
```
- References are read from `data/samples/correct_samples/` (`.txt` or `.vtt`), model outputs from the other folders in `data/samples/` (one folder per model, same file names).
- Only references marked `reference_checked = True` in `data/samples/samples_dataset.csv` are scored. Mark a file only after correcting it fully by ear. `--all-references` scores unchecked ones too, but those results are unreliable.
- References that look uncorrected are listed as warnings: identical to a model's output, containing text Whisper is known to invent (e.g. "Hvala što pratite kanal", repeated "Muzika", 🎵), or repeating the same phrase many times.
- Both texts are normalized the same way before scoring: Cyrillic converted to Latin, lowercase, punctuation, emoji and `[tags]` removed. Dialect spellings and numbers are kept as written.
- Metrics, lower is better unless noted:
  - **WER**: word error rate, the main metric, with a 95% confidence interval from bootstrapping over files.
  - **WER no-diacritics**: the same with č/ć/š/ž/đ simplified, the gap to WER shows how many errors are only diacritics.
  - **CER**: character error rate, kinder to small mistakes in word endings.
  - **sub / del / ins**: wrong, missing and extra words. High `ins` usually means invented text, high `del` means skipped sections.
  - **len**: model words divided by reference words, should be close to 1.
- Reference-free checks run on every model file: files where a 4-word phrase repeats 5+ times (Whisper looping) and files with known invented text.
- `--per-file` adds WER per file and per season, `--save` writes the results table to `evaluation/results/`.

### _About future contributions_: Guidelines and detailed documentation will be uploaded in the near future.

## About the TV Show
### Main data about show:
- Show aired: 2012.
- Number of episodes ~2300+
- Views 790,000,000+
- Languages: Serbian
- Secondary languages: German, Hungarian, English, Chinese, Slovakian, Greek
- Number of seasons: 13



