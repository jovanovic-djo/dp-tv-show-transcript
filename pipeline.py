"""Transcribe every episode: download audio, transcribe, save, delete audio, then the next episode.

Safe to stop at any time (Ctrl+C, closing the window, a crash) and run again, finished episodes are skipped.
"""
import argparse
import datetime
import importlib.util
import os
import shutil
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "data" / "clean_data" / "episodes.csv"
TRANSCRIPTS_DIR = ROOT / "data" / "transcripts"
AUDIO_DIR = TRANSCRIPTS_DIR / "audio"
PROGRESS_PATH = TRANSCRIPTS_DIR / "progress.csv"
PROGRESS_COLUMNS = ["name", "season", "episode_number", "url", "status", "audio_seconds",
                    "processing_seconds", "words", "error", "updated_at"]
# Several downloads failing in a row usually means YouTube is blocking or yt-dlp is outdated
MAX_DOWNLOAD_FAILURES_IN_A_ROW = 5


def load_module(name, path):
    # downloader/ and transcriber/ both have a utils.py, so they are loaded under their own names
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


downloader = load_module("downloader_utils", ROOT / "downloader" / "utils.py")
transcriber = load_module("transcriber_utils", ROOT / "transcriber" / "utils.py")


def length_seconds(length):
    seconds = 0
    for part in str(length).split(":"):
        seconds = seconds * 60 + int(part)
    return seconds


def format_hours(seconds):
    return f"{seconds / 3600:.1f} h"


def load_progress(path):
    if path.exists():
        return pd.read_csv(path, dtype={"error": str}).set_index("name", drop=False)
    return pd.DataFrame(columns=PROGRESS_COLUMNS).set_index("name", drop=False)


def save_progress(progress, path):
    temporary = path.with_name(path.name + ".tmp")
    progress = progress.astype({"season": "Int64", "episode_number": "Int64", "words": "Int64"})
    progress.sort_values(["season", "episode_number"]).to_csv(temporary, index=False, lineterminator="\n")
    os.replace(temporary, path)


def update_progress(progress, episode, **values):
    row = {"name": episode["name"], "season": episode["season"], "episode_number": episode["episode_number"],
           "url": episode["url"], "updated_at": datetime.datetime.now().isoformat(timespec="seconds"), "error": "", **values}
    for column, value in row.items():
        progress.loc[episode["name"], column] = value


def load_episodes(csv_path, seasons=None):
    df = pd.read_csv(csv_path)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    if seasons:
        df = df[df["season"].isin(seasons)]
    df["name"] = [downloader.get_name(r.season, r.episode_number, r.episode_name) for r in df.itertuples()]
    df["seconds"] = df["length"].map(length_seconds)
    return df.sort_values(["season", "episode_number"])


def process_episode(model, settings, model_info, episode, output_dir, quiet):
    """Download, transcribe and save one episode. The audio is always deleted afterwards."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    try:
        try:
            audio_path = downloader.download_episode(episode["url"], episode["name"], AUDIO_DIR, quiet=quiet)
        except Exception as e:
            raise DownloadError(str(e)) from e
        transcript = transcriber.transcribe_file(model, audio_path, settings, model_info)
        transcript["metadata"] = {key: episode[key] for key in ("season", "episode_number", "episode_name", "title", "date", "url")}
        transcriber.save_transcript(transcript, output_dir)
        return transcript
    finally:
        shutil.rmtree(AUDIO_DIR, ignore_errors=True)


class DownloadError(Exception):
    pass


def main():
    parser = argparse.ArgumentParser(description="Download, transcribe and save every episode, deleting the audio after each one.")
    parser.add_argument("--csv", type=Path, default=CSV_PATH, help="episode list, default: data/clean_data/episodes.csv")
    parser.add_argument("--seasons", type=int, nargs="+", help="only these seasons, e.g. --seasons 1 2")
    parser.add_argument("--limit", type=int, help="stop after this many episodes")
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--output-dir", type=Path, help="default: data/transcripts/fw_<model>")
    parser.add_argument("--sleep", type=float, default=5, help="seconds to wait between episodes, to go easy on YouTube")
    parser.add_argument("--skip-failed", action="store_true", help="don't retry episodes that failed before")
    parser.add_argument("--verbose", action="store_true", help="show yt-dlp output")
    args = parser.parse_args()

    output_dir = args.output_dir or TRANSCRIPTS_DIR / f"fw_{args.model}"
    episodes = load_episodes(args.csv, args.seasons)
    progress = load_progress(PROGRESS_PATH)
    done = {path.stem for path in output_dir.glob("*.json")} if output_dir.exists() else set()
    failed = set(progress.loc[progress["status"].str.endswith("failed", na=False), "name"])
    todo = episodes[~episodes["name"].isin(done)]
    if args.skip_failed:
        todo = todo[~todo["name"].isin(failed)]
    if args.limit:
        todo = todo.head(args.limit)

    print(f"{len(episodes)} episodes, {len(episodes) - len(todo)} done or skipped, {len(todo)} to go "
          f"({format_hours(todo['seconds'].sum())} of audio). Transcripts go to {output_dir}")
    if todo.empty:
        return

    shutil.rmtree(AUDIO_DIR, ignore_errors=True)  # leftovers from an interrupted run
    transcriber.keep_awake()
    model, device, compute_type = transcriber.load_model(args.model)
    model_info = {"model": args.model, "device": device, "compute_type": compute_type}
    settings = transcriber.transcription_settings()

    started, audio_done, download_failures = time.time(), 0, 0
    try:
        for number, episode in enumerate(todo.to_dict("records"), start=1):
            prefix = f"[{number}/{len(todo)}] {episode['name']}"
            try:
                transcript = process_episode(model, settings, model_info, episode, output_dir, quiet=not args.verbose)
            except DownloadError as e:
                download_failures += 1
                update_progress(progress, episode, status="download failed", error=str(e)[:300])
                print(f"{prefix}: download failed: {e}")
                if download_failures >= MAX_DOWNLOAD_FAILURES_IN_A_ROW:
                    print(f"{download_failures} downloads failed in a row, stopping. Update yt-dlp (pip install -U yt-dlp) "
                          "or wait a while if YouTube is blocking, then run again.")
                    break
                continue
            except Exception as e:
                update_progress(progress, episode, status="transcription failed", error=str(e)[:300])
                print(f"{prefix}: transcription failed: {e}")
                continue
            finally:
                save_progress(progress, PROGRESS_PATH)

            download_failures = 0
            update_progress(progress, episode, status="done", audio_seconds=transcript["duration"],
                            processing_seconds=transcript["processing_seconds"], words=len(transcript["text"].split()))
            save_progress(progress, PROGRESS_PATH)

            audio_done += episode["seconds"]
            remaining = todo["seconds"].iloc[number:].sum()
            eta = remaining * (time.time() - started) / audio_done
            print(f"{prefix}: {transcript['duration']:.0f}s audio, {len(transcript['text'].split())} words, "
                  f"{transcript['processing_seconds']:.0f}s | about {format_hours(eta)} left")
            if number < len(todo):
                time.sleep(args.sleep)
    except KeyboardInterrupt:
        print("\nStopped. Run the same command again to continue where it left off.")
    finally:
        shutil.rmtree(AUDIO_DIR, ignore_errors=True)


if __name__ == "__main__":
    main()
