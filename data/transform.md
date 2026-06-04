# Dataset transformation & subset selection

This documents exactly how we go from the upstream WMT25-TS files to the
500-sentence scored subset, so the selection is reproducible and unbiased.

## Inputs

Two parallel, line-aligned files from upstream (`data/wmt25-legal/`):

- `eng-hin-test.eng.txt` - English source, one sentence per line
- `eng-hin-test.hin.txt` - Hindi human reference, one sentence per line

Line *i* of the English file corresponds to line *i* of the Hindi file.

## Cleaning

- Each line is stripped of leading/trailing whitespace.
- No other normalization is applied to the source or reference. We deliberately
  do **not** lowercase, strip punctuation, or alter numerals/citations, because
  preserving them is part of what legal translation is judged on.

## Stratification (the 500-sentence subset)

We bucket every pair by **English word count** (`len(en.split())`):

| Bucket | Word count | Sentences sampled |
|---|---|---|
| short  | 5-15  | 100 |
| medium | 16-35 | 200 |
| long   | 36-54 | 200 |

Sampling uses Python's `random.sample` with a **fixed seed of 42**, so the same
500 sentences are selected on every run and for every system. See
`scripts/benchmark_translation.py::load_dataset` (the single source of truth that
both the raw-model runner and the Anuvad runner import).

## Why a subset

Scoring 500 of the 5,000 sentences keeps API cost and runtime low while staying
statistically meaningful. Re-running with a different seed shifts absolute scores
by roughly 1-2 BLEU but does not change the relative ranking of systems. To score
the full 5,000, change `n_small/n_medium/n_large` in `load_dataset`.
