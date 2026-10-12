import argparse
import datetime
import importlib.util
import json
import random
import re
from pathlib import Path

import jiwer
import pandas as pd

from text_utils import max_repeated_ngram, normalize


ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = ROOT / "data" / "samples"
REFERENCE_DIR = SAMPLES_DIR / "correct_samples"
SAMPLES_CSV = SAMPLES_DIR / "samples_dataset.csv"
RESULTS_DIR = ROOT / "evaluation" / "results"

NON_MODEL_DIRS = {"audio", "correct_samples", "ground_truth"}
TRANSCRIPT_EXTENSIONS = (".vtt", ".txt", ".json")
LOOP_THRESHOLD = 5
# Text Whisper is known to invent over music and silence
SUSPICIOUS_PHRASES = ["hvala što pratite", "hvala na gledanju", "pretplatite se", "muzika muzika"]


def load_get_name():
    spec = importlib.util.spec_from_file_location("downloader_utils", ROOT / "downloader" / "utils.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.get_name


def parse_vtt(text):
    lines = []
    in_note = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            in_note = False
            continue
        if line.startswith("NOTE"):
            in_note = True
        if in_note or line == "WEBVTT" or "-->" in line or line.isdigit():
            continue
        lines.append(re.sub(r"<[^>]+>", "", line))
    return " ".join(lines)


def read_transcript(path):
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".vtt":
        return parse_vtt(text)
    if path.suffix == ".json":
        return json.loads(text)["text"]
    return text


def load_transcripts(directory):
    transcripts = {}
    for path in sorted(directory.iterdir()):
        if path.suffix in TRANSCRIPT_EXTENSIONS and path.stem not in transcripts:
            transcripts[path.stem] = read_transcript(path)
    return transcripts


def find_models(names):
    if names:
        return {Path(name).name: (Path(name) if Path(name).is_dir() else SAMPLES_DIR / name) for name in names}
    return {
        path.name: path
        for path in sorted(SAMPLES_DIR.iterdir())
        if path.is_dir() and path.name not in NON_MODEL_DIRS and any(p.suffix in TRANSCRIPT_EXTENSIONS for p in path.iterdir())
    }


def checked_references(csv_path):
    df = pd.read_csv(csv_path)
    if "reference_checked" not in df.columns:
        return set()
    get_name = load_get_name()
    checked = df[df["reference_checked"] == True]
    return {get_name(row["season"], row["episode_number"], row["episode_name"]) for _, row in checked.iterrows()}


def reference_warnings(reference, model_outputs):
    warnings = [f"identical to {model}" for model, text in model_outputs.items() if text.strip() == reference.strip()]
    normalized = normalize(reference)
    warnings += [f'contains "{phrase}"' for phrase in SUSPICIOUS_PHRASES if phrase in normalized]
    if "🎵" in reference:
        warnings.append("contains 🎵")
    repeats = max_repeated_ngram(reference)
    if repeats >= LOOP_THRESHOLD:
        warnings.append(f"a 4-word phrase repeats {repeats}x")
    return warnings


def file_errors(reference, hypothesis):
    output = jiwer.process_words(reference, hypothesis)
    return output.substitutions + output.deletions + output.insertions, output.hits + output.substitutions + output.deletions


def bootstrap_wer(references, hypotheses, rounds, seed=0):
    counts = [file_errors(ref, hyp) for ref, hyp in zip(references, hypotheses)]
    rng = random.Random(seed)
    samples = []
    for _ in range(rounds):
        picked = [rng.choice(counts) for _ in counts]
        samples.append(sum(e for e, _ in picked) / sum(n for _, n in picked))
    samples.sort()
    return samples[int(0.025 * rounds)], samples[int(0.975 * rounds) - 1]


def score(references, hypotheses, bootstrap_rounds):
    refs = [normalize(text) for text in references]
    hyps = [normalize(text) for text in hypotheses]
    words = jiwer.process_words(refs, hyps)
    ref_words = words.hits + words.substitutions + words.deletions

    plain_refs = [normalize(text, keep_diacritics=False) for text in references]
    plain_hyps = [normalize(text, keep_diacritics=False) for text in hypotheses]

    row = {
        "WER": words.wer,
        "WER no-diacritics": jiwer.process_words(plain_refs, plain_hyps).wer,
        "CER": jiwer.process_characters(refs, hyps).cer,
        "sub": words.substitutions / ref_words,
        "del": words.deletions / ref_words,
        "ins": words.insertions / ref_words,
        "len": sum(len(h.split()) for h in hyps) / ref_words,
    }
    if bootstrap_rounds:
        low, high = bootstrap_wer(refs, hyps, bootstrap_rounds)
        row["WER 95% CI"] = f"{low:.1%}-{high:.1%}"
    return row


def season_of(name):
    match = re.match(r"s(\d+)ep", name)
    return int(match.group(1)) if match else None


def percent(df, columns):
    df = df.copy()
    for column in columns:
        if column in df:
            df[column] = df[column].map(lambda v: f"{v:.1%}")
    return df


def main():
    parser = argparse.ArgumentParser(description="Score model transcripts against hand-corrected references.")
    parser.add_argument("--references", type=Path, default=REFERENCE_DIR, help="folder of reference .txt/.vtt files")
    parser.add_argument("--models", nargs="*", help="model output folders (names inside data/samples or paths), default: all")
    parser.add_argument("--samples-csv", type=Path, default=SAMPLES_CSV, help="CSV with the reference_checked column")
    parser.add_argument("--all-references", action="store_true", help="also score references not marked as checked")
    parser.add_argument("--per-file", action="store_true", help="show WER per file and per season")
    parser.add_argument("--show", metavar="NAME", help="show the word alignment for one file, e.g. s1ep1-Rakija")
    parser.add_argument("--bootstrap", type=int, default=1000, help="bootstrap rounds for the WER confidence interval, 0 to skip")
    parser.add_argument("--save", action="store_true", help="save the results table to evaluation/results/")
    args = parser.parse_args()

    references = load_transcripts(args.references)
    models = {name: load_transcripts(path) for name, path in find_models(args.models).items()}
    checked = checked_references(args.samples_csv) & set(references)

    print(f"References: {len(references)} in {args.references}, {len(checked)} marked as checked\n")
    flagged = {}
    for name, text in references.items():
        warnings = reference_warnings(text, {model: outputs[name] for model, outputs in models.items() if name in outputs})
        if warnings:
            flagged[name] = warnings
    if flagged:
        print(f"Reference warnings ({len(flagged)} files):")
        for name, warnings in flagged.items():
            status = "checked" if name in checked else "not checked"
            print(f"  {name} [{status}]: {'; '.join(warnings)}")
        print()

    to_score = sorted(set(references) if args.all_references else checked)
    if not to_score:
        print("No references to score. Set reference_checked to True in samples_dataset.csv for corrected files,")
        print("or pass --all-references to score unchecked ones anyway.\n")

    rows, per_file = [], []
    for model, outputs in models.items():
        names = [name for name in to_score if name in outputs and normalize(references[name])]
        missing = len(to_score) - len(names)
        if names:
            row = {"model": model, "files": len(names), "missing": missing}
            row.update(score([references[n] for n in names], [outputs[n] for n in names], args.bootstrap))
            rows.append(row)
            for name in names:
                errors, ref_words = file_errors(normalize(references[name]), normalize(outputs[name]))
                per_file.append({"model": model, "file": name, "season": season_of(name), "errors": errors, "ref_words": ref_words})

    if rows:
        label = "all references, including unchecked" if args.all_references else "checked references only"
        print(f"Accuracy ({label}, lower is better):")
        table = percent(pd.DataFrame(rows), ["WER", "WER no-diacritics", "CER", "sub", "del", "ins"])
        table["len"] = table["len"].map(lambda v: f"{v:.2f}")
        print(table.to_string(index=False), "\n")

    print("Reference-free checks (all files of each model):")
    loops = []
    for model, outputs in models.items():
        repeats = {name: max_repeated_ngram(text) for name, text in outputs.items()}
        looping = [name for name, count in repeats.items() if count >= LOOP_THRESHOLD]
        suspicious = [name for name, text in outputs.items() if "🎵" in text or any(p in normalize(text) for p in SUSPICIOUS_PHRASES)]
        loops.append({
            "model": model,
            "files": len(outputs),
            "files with loops": len(looping),
            "worst loop": max(repeats.values(), default=0),
            "files with known invented text": len(suspicious),
        })
    print(pd.DataFrame(loops).to_string(index=False), "\n")

    if args.per_file and per_file:
        df = pd.DataFrame(per_file)
        files = df.pivot(index="file", columns="model", values="errors") / df.pivot(index="file", columns="model", values="ref_words")
        print("WER per file:")
        print(files.map(lambda v: f"{v:.1%}").to_string(), "\n")
        seasons = df.groupby(["season", "model"])[["errors", "ref_words"]].sum()
        seasons = (seasons["errors"] / seasons["ref_words"]).unstack("model")
        print("WER per season:")
        print(seasons.map(lambda v: f"{v:.1%}").to_string(), "\n")

    if args.show:
        if args.show not in references:
            print(f"No reference named {args.show}")
        for model, outputs in models.items():
            if args.show in references and args.show in outputs:
                print(f"=== {model} ===")
                alignment = jiwer.process_words(normalize(references[args.show]), normalize(outputs[args.show]))
                print(jiwer.visualize_alignment(alignment, show_measures=False))

    if args.save and rows:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        path = RESULTS_DIR / f"{datetime.date.today()}.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        print(f"Saved results to {path}")


if __name__ == "__main__":
    main()
