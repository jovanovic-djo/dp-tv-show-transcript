This data is for measuring accuracy of the different approaches.

- `samples_dataset.csv`: the sample episodes. `downloaded` tracks audio downloads, `reference_checked` marks references that were fully corrected by ear and can be used for scoring.
- `correct_samples/`: hand-corrected reference transcripts.
- `whisper_base/`, `whisper_small/`, `whisper_medium/`, `whisper_large/`: model outputs, one folder per model with the same file names as the references.

Score them with `python evaluation/evaluate.py` (see the main README).
