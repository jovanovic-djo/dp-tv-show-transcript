This data is for measuring accuracy of the different approaches.

- `samples_dataset.csv`: the sample episodes. `downloaded` tracks audio downloads, `reference_checked` marks references that were fully corrected by ear and can be used for scoring.
- `correct_samples/`: hand-corrected reference transcripts (`.vtt` with speakers, or older `.txt`), see `docs/correction_guide.md`.
- `drafts/`: uncorrected WebVTT drafts made by `transcriber/json_to_vtt.py`.
- `whisper_base/`, `whisper_small/`, `whisper_medium/`, `whisper_large/`, `fw_<model>/`: model outputs, one folder per model with the same file names as the references.

The transcript folders are not tracked in git (see `.gitignore`), they only exist locally. Model outputs can be regenerated with `python transcriber/utils.py`.

Score them with `python evaluation/evaluate.py` (see the main README).
