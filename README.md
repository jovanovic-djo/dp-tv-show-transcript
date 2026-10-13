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
- Upload episode/Provide a link to the 3rd party tool which would generate a transcript of the episode, manually or with automation. (Selenium)
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
- Each JSON has the full `text`, `segments` with start/end times and word timestamps, the model and settings used, and processing time.
- Keeps Windows awake while running (closing a laptop lid still sleeps). On laptops, make sure the GPU is not power-limited by the manufacturer's power mode, `nvidia-smi -q -d POWER` shows the current limit.

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



