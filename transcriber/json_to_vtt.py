import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = ROOT / "data" / "samples"
INPUT_DIR = SAMPLES_DIR / "fw_large-v3"
OUTPUT_DIR = SAMPLES_DIR / "drafts"

# Markers for the person correcting the draft. Both are ignored by evaluation/evaluate.py
# if left in by mistake, and it warns about references that still contain them.
UNSURE_MARK = "(?)"
GAP_TEXT = "[CHECK: no text here, missed speech?]"
SENTENCE_END = re.compile(r"[.?!…]+[\"'»]*$")
TRAILING_PUNCTUATION = re.compile(r"([^\w]*)$")


def format_time(seconds):
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def mark_word(word, min_probability):
    """Put the unsure mark before trailing punctuation: 'vurica,' -> 'vurica(?),'."""
    text = word["word"]
    if word["probability"] >= min_probability:
        return text
    punctuation = TRAILING_PUNCTUATION.search(text).group(1)
    return text[: len(text) - len(punctuation)] + UNSURE_MARK + punctuation


def segment_cues(segment, min_probability, split_sentences):
    """One cue per sentence, since a new sentence is often a new speaker."""
    words = segment.get("words")
    if not words:
        return [(segment["start"], segment["end"], segment["text"])]

    cues, current = [], []
    for word in words:
        current.append(word)
        if split_sentences and SENTENCE_END.search(word["word"]):
            cues.append(current)
            current = []
    if current:
        cues.append(current)

    return [
        (cue[0]["start"], cue[-1]["end"], " ".join(mark_word(w, min_probability) for w in cue))
        for cue in cues
    ]


def build_cues(transcript, min_probability=0.5, min_gap=10, split_sentences=True):
    cues = []
    for segment in transcript["segments"]:
        cues += segment_cues(segment, min_probability, split_sentences)

    # Flag long stretches without text, they can be music or missed dialogue
    with_gaps, previous_end = [], 0.0
    for start, end, text in cues + [(transcript["duration"], transcript["duration"], None)]:
        if start - previous_end >= min_gap:
            with_gaps.append((previous_end, start, GAP_TEXT))
        if text is not None:
            with_gaps.append((start, end, text))
        previous_end = max(previous_end, end)
    return with_gaps


def to_vtt(transcript, cues, min_probability):
    lines = [
        "WEBVTT",
        "",
        f"NOTE Draft from {transcript.get('engine', '')} {transcript.get('model', '')}, {transcript['source_file']}.",
        f"Words marked {UNSURE_MARK} had confidence below {min_probability}, {GAP_TEXT} marks long stretches without text.",
        "Correct by ear, add speakers as <v Name>, remove all markers, see docs/correction_guide.md.",
        "",
    ]
    for start, end, text in cues:
        lines += [f"{format_time(start)} --> {format_time(end)}", text, ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Turn transcriber JSON files into WebVTT drafts for hand correction.")
    parser.add_argument("episodes", nargs="*", help="episode names or JSON files, default: all JSON files in --input-dir")
    parser.add_argument("--input-dir", type=Path, default=INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--min-probability", type=float, default=0.5, help="words below this confidence get marked (?), 0 to disable")
    parser.add_argument("--min-gap", type=float, default=10, help="flag stretches without text at least this many seconds long")
    parser.add_argument("--no-split", action="store_true", help="one cue per Whisper segment instead of per sentence")
    parser.add_argument("--overwrite", action="store_true", help="replace existing drafts")
    args = parser.parse_args()

    if args.episodes:
        paths = [Path(e) if Path(e).suffix == ".json" else args.input_dir / f"{e}.json" for e in args.episodes]
    else:
        paths = sorted(args.input_dir.glob("*.json"))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        output = args.output_dir / f"{path.stem}.vtt"
        if not path.exists():
            print(f"Missing {path}")
            continue
        if output.exists() and not args.overwrite:
            print(f"Skipped {output.name}, already exists (use --overwrite)")
            continue
        transcript = json.loads(path.read_text(encoding="utf-8"))
        cues = build_cues(transcript, args.min_probability, args.min_gap, not args.no_split)
        output.write_text(to_vtt(transcript, cues, args.min_probability), encoding="utf-8", newline="\n")
        gaps = sum(text == GAP_TEXT for _, _, text in cues)
        print(f"Saved {output.relative_to(ROOT) if output.is_relative_to(ROOT) else output}: {len(cues)} cues, {gaps} gaps to check")


if __name__ == "__main__":
    main()
