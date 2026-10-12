import argparse
import datetime
import glob
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluation"))
from text_utils import cyrillic_to_latin, normalize  # noqa: E402


INPUT_DIR = ROOT / "data" / "samples" / "audio"
SAMPLES_DIR = ROOT / "data" / "samples"
AUDIO_EXTENSIONS = (".webm", ".m4a", ".opus", ".mp3", ".wav")

# Steers Whisper towards Latin script and the correct spelling of the main characters
INITIAL_PROMPT = "Razgovor na srpskom jeziku, latinicom."
HOTWORDS = "Đorđe Čvarkov Dragan Torbica Boškić"

# Text Whisper invents over music, silence and laughter, compared after normalize()
INVENTED_PHRASES = ["hvala što pratite", "hvala na gledanju", "pretplatite se", "titlovi", "prevod i obrada"]
NON_SPEECH = {"muzika", "smeh", "aplauz"}
MAX_REPEATED_SEGMENTS = 2


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
        "hotwords": HOTWORDS,
    }
    if batch_size:
        settings["batch_size"] = batch_size
    return settings


def removal_reason(text, previous_texts):
    normalized = normalize(text)
    if not normalized or set(normalized.split()) <= NON_SPEECH:
        return "non-speech"
    if normalize(INITIAL_PROMPT) in normalized:
        return "prompt leaked into transcript"
    for phrase in INVENTED_PHRASES:
        if phrase in normalized:
            return f'invented phrase "{phrase}"'
    if previous_texts[-MAX_REPEATED_SEGMENTS:] == [normalized] * MAX_REPEATED_SEGMENTS:
        return "repeated segment"
    return None


def clean_segments(segments):
    """Convert to Latin script and drop segments Whisper most likely invented, keeping a record of what was removed."""
    kept, removed, previous_texts = [], [], []
    for segment in segments:
        text = cyrillic_to_latin(segment.text.strip())
        entry = {"start": round(segment.start, 2), "end": round(segment.end, 2), "text": text}
        if segment.words:
            entry["words"] = [
                {"start": round(w.start, 2), "end": round(w.end, 2), "word": cyrillic_to_latin(w.word.strip()), "probability": round(w.probability, 3)}
                for w in segment.words
            ]

        reason = removal_reason(text, previous_texts)
        if reason:
            removed.append({"start": entry["start"], "end": entry["end"], "text": text, "reason": reason})
        else:
            kept.append(entry)
        previous_texts.append(normalize(text))
    return kept, removed


def transcribe_file(model, audio_path, settings, model_info):
    audio_path = Path(audio_path)
    started = time.time()
    segments, info = model.transcribe(str(audio_path), **settings)
    kept, removed = clean_segments(segments)
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
    }


def save_transcript(transcript, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{transcript['episode']}.json"
    temporary = path.with_name(path.name + ".tmp")
    with open(temporary, "w", encoding="utf-8") as file:
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
    parser.add_argument("--overwrite", action="store_true", help="transcribe files that already have a transcript")
    args = parser.parse_args()

    output_dir = args.output_dir or SAMPLES_DIR / f"fw_{args.model}"
    audio_files = find_audio(args.input)
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
            transcript = transcribe_file(model, audio_path, settings, model_info)
        except Exception as e:
            print(f"[{number}/{len(todo)}] Failed {audio_path.name}: {e}")
            continue
        save_transcript(transcript, output_dir)
        speed = transcript["duration"] / max(transcript["processing_seconds"], 0.1)
        print(f"[{number}/{len(todo)}] {audio_path.stem}: {transcript['duration']:.0f}s audio in "
              f"{transcript['processing_seconds']:.0f}s ({speed:.1f}x), removed {len(transcript['removed_segments'])} segments")


if __name__ == "__main__":
    main()
