import argparse
import datetime
import glob
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluation"))
from text_utils import cyrillic_to_latin, normalize  # noqa: E402


INPUT_DIR = ROOT / "data" / "samples" / "audio"
SAMPLES_DIR = ROOT / "data" / "samples"
AUDIO_EXTENSIONS = (".webm", ".m4a", ".opus", ".mp3", ".wav")

# Steers Whisper towards Latin script. Hotwords with character names are not used,
# they made Whisper skip whole 30-second windows of dialogue.
INITIAL_PROMPT = "Razgovor na srpskom jeziku, latinicom."

# Text Whisper invents over music, silence and laughter, compared after normalize()
INVENTED_PHRASES = ["hvala što pratite", "hvala na gledanju", "pretplatite se", "titlovi", "prevod i obrada"]
NON_SPEECH = {"muzika", "smeh", "aplauz"}
LAUGHTER = re.compile(r"^(ha|he|hi)(ha|he|hi)+h?$")
MAX_REPEATED_SEGMENTS = 2

# Whisper sometimes returns nothing for a whole stretch of dialogue. Stretches without text that
# contain speech are transcribed again on their own, and the result is kept only if Whisper is confident.
MIN_GAP_SECONDS = 5
MIN_GAP_SPEECH_SECONDS = 3
GAP_MIN_AVG_LOGPROB = -1.0
GAP_MAX_NO_SPEECH_PROB = 0.6
GAP_MAX_COMPRESSION_RATIO = 2.4
SAMPLING_RATE = 16000


def add_cuda_libraries():
    """Let CTranslate2 find the CUDA 12 libraries installed by the nvidia-* pip packages (needed on Windows)."""
    try:
        import nvidia
    except ImportError:
        return
    for package_dir in nvidia.__path__:
        for bin_dir in glob.glob(os.path.join(package_dir, "*", "bin")):
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(bin_dir)
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ["PATH"]


def keep_awake():
    """Stop Windows from sleeping while this process runs (closing the lid still sleeps)."""
    if sys.platform == "win32":
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)


def load_model(model_name, device="auto", compute_type="auto", batch_size=0):
    add_cuda_libraries()
    import ctranslate2
    from faster_whisper import BatchedInferencePipeline, WhisperModel

    if device == "auto":
        device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    if compute_type == "auto":
        compute_type = "int8_float16" if device == "cuda" else "int8"

    print(f"Loading {model_name} on {device} ({compute_type})")
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    if batch_size:
        model = BatchedInferencePipeline(model=model)
    return model, device, compute_type


def transcription_settings(beam_size=5, vad=True, word_timestamps=True, batch_size=0):
    settings = {
        "language": "sr",
        "beam_size": beam_size,
        "vad_filter": vad,
        "condition_on_previous_text": False,
        "word_timestamps": word_timestamps,
        "initial_prompt": INITIAL_PROMPT,
    }
    if batch_size:
        settings["batch_size"] = batch_size
    return settings


def removal_reason(text, previous_texts):
    normalized = normalize(text)
    if not normalized or all(word in NON_SPEECH or LAUGHTER.match(word) for word in normalized.split()):
        return "non-speech"
    if normalize(INITIAL_PROMPT) in normalized:
        return "prompt leaked into transcript"
    for phrase in INVENTED_PHRASES:
        if phrase in normalized:
            return f'invented phrase "{phrase}"'
    if previous_texts[-MAX_REPEATED_SEGMENTS:] == [normalized] * MAX_REPEATED_SEGMENTS:
        return "repeated segment"
    return None


def low_confidence_reason(segment):
    if segment.no_speech_prob > GAP_MAX_NO_SPEECH_PROB:
        return "gap fill: probably not speech"
    if segment.avg_logprob < GAP_MIN_AVG_LOGPROB:
        return "gap fill: low confidence"
    if segment.compression_ratio > GAP_MAX_COMPRESSION_RATIO:
        return "gap fill: repetitive text"
    return None


def clean_segments(segments, gap_fill=False):
    """Convert to Latin script and drop segments Whisper most likely invented, keeping a record of what was removed."""
    kept, removed, previous_texts = [], [], []
    for segment in segments:
        text = cyrillic_to_latin(segment.text.strip())
        entry = {"start": round(segment.start, 2), "end": round(segment.end, 2), "text": text}
        if gap_fill:
            entry["gap_fill"] = True
        if segment.words:
            entry["words"] = [
                {"start": round(w.start, 2), "end": round(w.end, 2), "word": cyrillic_to_latin(w.word.strip()), "probability": round(w.probability, 3)}
                for w in segment.words
            ]

        reason = removal_reason(text, previous_texts) or (low_confidence_reason(segment) if gap_fill else None)
        if reason:
            removed.append({"start": entry["start"], "end": entry["end"], "text": text, "reason": reason})
        else:
            kept.append(entry)
        previous_texts.append(normalize(text))
    return kept, removed


def find_gaps(segments, duration, speech, min_gap=MIN_GAP_SECONDS, min_speech=MIN_GAP_SPEECH_SECONDS):
    """Stretches of at least min_gap seconds without text that contain at least min_speech seconds of detected speech."""
    gaps, previous_end = [], 0.0
    for start, end in [(s["start"], s["end"]) for s in segments] + [(duration, duration)]:
        if start - previous_end >= min_gap:
            speech_seconds = sum(max(0.0, min(start, b) - max(previous_end, a)) for a, b in speech)
            if speech_seconds >= min_speech:
                gaps.append((previous_end, start))
        previous_end = max(previous_end, end)
    return gaps


def fill_gaps(model, audio_path, segments, duration, settings):
    """Transcribe stretches Whisper left empty again, one at a time, without voice activity detection."""
    from faster_whisper import WhisperModel
    from faster_whisper.audio import decode_audio
    from faster_whisper.vad import get_speech_timestamps

    audio = decode_audio(str(audio_path), sampling_rate=SAMPLING_RATE)
    speech = [(t["start"] / SAMPLING_RATE, t["end"] / SAMPLING_RATE) for t in get_speech_timestamps(audio)]
    gaps = find_gaps(segments, duration, speech)

    # Gaps are transcribed with the plain model, the batched pipeline takes clips in a different format
    whisper = model if isinstance(model, WhisperModel) else model.model
    gap_settings = {k: v for k, v in settings.items() if k not in ("vad_filter", "batch_size")}
    added, removed, checked = [], [], []
    for start, end in gaps:
        gap_segments, _ = whisper.transcribe(audio, clip_timestamps=[start, end], **gap_settings)
        # Keep only what falls inside the gap, the clip can run slightly past its end
        gap_kept, gap_removed = clean_segments([s for s in gap_segments if s.start < end and s.end > start], gap_fill=True)
        added += gap_kept
        removed += gap_removed
        checked.append({"start": round(start, 2), "end": round(end, 2), "added_words": sum(len(s["text"].split()) for s in gap_kept)})
    return added, removed, checked


def transcribe_file(model, audio_path, settings, model_info, gap_fill=True):
    audio_path = Path(audio_path)
    started = time.time()
    segments, info = model.transcribe(str(audio_path), **settings)
    kept, removed = clean_segments(segments)
    gaps_checked = []
    if gap_fill:
        added, gap_removed, gaps_checked = fill_gaps(model, audio_path, kept, info.duration, settings)
        kept = sorted(kept + added, key=lambda s: s["start"])
        removed = sorted(removed + gap_removed, key=lambda s: s["start"])
    processing_seconds = time.time() - started

    return {
        "episode": audio_path.stem,
        "source_file": audio_path.name,
        "text": " ".join(segment["text"] for segment in kept),
        "duration": round(info.duration, 2),
        "processing_seconds": round(processing_seconds, 1),
        "transcribed_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "engine": "faster-whisper",
        **model_info,
        "settings": settings,
        "segments": kept,
        "removed_segments": removed,
        "gaps_checked": gaps_checked,
    }


def fill_existing(model, audio_path, json_path):
    """Run the gap fill on a transcript made before it existed, with the settings stored in it."""
    transcript = json.loads(Path(json_path).read_text(encoding="utf-8"))
    started = time.time()
    added, removed, gaps_checked = fill_gaps(model, audio_path, transcript["segments"], transcript["duration"], transcript["settings"])
    transcript["segments"] = sorted(transcript["segments"] + added, key=lambda s: s["start"])
    transcript["removed_segments"] = sorted(transcript["removed_segments"] + removed, key=lambda s: s["start"])
    transcript["gaps_checked"] = gaps_checked
    transcript["text"] = " ".join(segment["text"] for segment in transcript["segments"])
    transcript["processing_seconds"] = round(transcript["processing_seconds"] + time.time() - started, 1)
    return transcript


def save_transcript(transcript, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{transcript['episode']}.json"
    temporary = path.with_name(path.name + ".tmp")
    with open(temporary, "w", encoding="utf-8", newline="\n") as file:
        json.dump(transcript, file, ensure_ascii=False, indent=1)
    os.replace(temporary, path)
    return path


def find_audio(input_path):
    input_path = Path(input_path)
    if input_path.is_file():
        return [input_path]
    return sorted(p for p in input_path.iterdir() if p.suffix.lower() in AUDIO_EXTENSIONS)


def main():
    parser = argparse.ArgumentParser(description="Transcribe episode audio with faster-whisper.")
    parser.add_argument("--input", type=Path, default=INPUT_DIR, help="audio file or folder")
    parser.add_argument("--output-dir", type=Path, help="where JSON transcripts are saved, default: data/samples/fw_<model>")
    parser.add_argument("--model", default="large-v3", help="e.g. large-v3, large-v3-turbo, medium, small")
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    parser.add_argument("--compute-type", default="auto", help="auto picks int8_float16 on GPU, int8 on CPU")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=0, help="batched inference, faster but uses more VRAM, 0 to disable")
    parser.add_argument("--no-vad", action="store_true", help="disable voice activity detection")
    parser.add_argument("--no-word-timestamps", action="store_true")
    parser.add_argument("--no-gap-fill", action="store_true", help="don't transcribe stretches without text again")
    parser.add_argument("--fill-existing", action="store_true",
                        help="only run the gap fill on transcripts that already exist and don't have it yet")
    parser.add_argument("--overwrite", action="store_true", help="transcribe files that already have a transcript")
    args = parser.parse_args()

    output_dir = args.output_dir or SAMPLES_DIR / f"fw_{args.model}"
    audio_files = find_audio(args.input)
    if args.fill_existing:
        todo = [p for p in audio_files if (output_dir / f"{p.stem}.json").exists()
                and "gaps_checked" not in json.loads((output_dir / f"{p.stem}.json").read_text(encoding="utf-8"))]
        print(f"{len(todo)} transcripts in {output_dir} without gap fill")
    else:
        todo = [p for p in audio_files if args.overwrite or not (output_dir / f"{p.stem}.json").exists()]
        print(f"{len(audio_files)} audio files, {len(audio_files) - len(todo)} already transcribed in {output_dir}")
    if not todo:
        return

    keep_awake()
    model, device, compute_type = load_model(args.model, args.device, args.compute_type, args.batch_size)
    model_info = {"model": args.model, "device": device, "compute_type": compute_type}
    settings = transcription_settings(args.beam_size, not args.no_vad, not args.no_word_timestamps, args.batch_size)

    for number, audio_path in enumerate(todo, start=1):
        try:
            if args.fill_existing:
                transcript = fill_existing(model, audio_path, output_dir / f"{audio_path.stem}.json")
            else:
                transcript = transcribe_file(model, audio_path, settings, model_info, not args.no_gap_fill)
        except Exception as e:
            print(f"[{number}/{len(todo)}] Failed {audio_path.name}: {e}")
            continue
        save_transcript(transcript, output_dir)
        speed = transcript["duration"] / max(transcript["processing_seconds"], 0.1)
        added = sum(gap["added_words"] for gap in transcript.get("gaps_checked", []))
        print(f"[{number}/{len(todo)}] {audio_path.stem}: {transcript['duration']:.0f}s audio in "
              f"{transcript['processing_seconds']:.0f}s ({speed:.1f}x), removed {len(transcript['removed_segments'])} segments, "
              f"{len(transcript.get('gaps_checked', []))} gaps checked, {added} words added")

if __name__ == "__main__":
    main()
