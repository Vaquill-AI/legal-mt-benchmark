# Legal Machine Translation Benchmark (English → Hindi)

A reproducible, **unbiased** benchmark of English-to-Hindi **legal** machine
translation. It scores raw LLM / NMT models and finished translation **products**
on the same data, with the same code, on the same metrics, and publishes every
per-sentence output so anyone can re-score or audit the numbers.

Maintained by [Vaquill AI](https://www.vaquill.ai). Contributions and
independent re-runs welcome.

> This is a **benchmark**, not a leaderboard ad. We report how each system did on
> each metric, document exactly how scores are computed, and disclose every
> caveat. No latency or price ranking is used to flatter any system.

---

## Why this exists

General MT benchmarks do not reflect **legal** translation, where a wrong term
("acquittal" → "dismissal from service") changes meaning, and where section
numbers, citations and dates must survive verbatim. We benchmark on a
peer-reviewed legal test suite and add a legal-terminology metric on top.

---

## Dataset

**WMT25 Legal Domain Test Suite**, by the **AI & NLP Research Group, IIT Patna**,
published at the Tenth Conference on Machine Translation (WMT 2025).

- Upstream: https://github.com/helloboyn/WMT25-TS
- Paper: Singh, K.B., Kumar, D., & Ekbal, A. (2025). *Evaluation of LLM for
  English to Hindi Legal Domain Machine Translation Systems.* WMT 2025,
  pp. 823–833. https://aclanthology.org/2025.wmt-1.57
- 5,000 parallel EN–HI sentences from court judgments, contracts, legal notices
  and statutory material; word counts 5–54.

We do **not** redistribute the upstream data. `data/fetch_dataset.sh` downloads it
from the source; `data/transform.md` documents exactly how we stratify it.

### Our subset (deterministic)

A stratified **500-sentence** subset, fixed **seed = 42**:
100 short (5–15 words) + 200 medium (16–35) + 200 long (36–54). Same seed → same
sentences for every system.

---

## Systems

**Raw models** (simple prompt, no glossary): GPT-5.4, GPT-5.4-mini, GPT-4o,
GPT-4o-mini, GPT-4.1, GPT-4.1-mini, Sarvam Translate v1, Google Translate.

**Products** (a base engine + a domain layer): **Anuvad** on three bases
(`gpt54`, `gpt54mini`, `sarvam`). Anuvad adds an 83,355-term legal glossary
(Government of India's Vidhi Shabdavali), legal-term / citation / date / currency
preservation, and a review pass. This lets us measure the **lift the product
layer adds on each base model**.

---

## Metrics — and how to read them

| Metric | Direction | What it measures | Reading a change |
|---|---|---|---|
| **BLEU** | higher = better | word n-gram overlap with the human reference | **<1 pt ≈ noise**; 1–2 = modest/real; 3–5 = clearly better; 5+ = large. Legal-Hindi BLEU is low in absolute terms (~24–31); never compare across language pairs. |
| **CHRF++** | higher = better | character n-gram F-score (word_order=2) | more reliable than BLEU for Hindi morphology; 1–2 pts is meaningful; correlates better with humans. |
| **METEOR** | higher = better | overlap with stem/synonym credit | more lenient than BLEU; useful as a cross-check. |
| **TER** | **lower = better** | Translation Edit Rate: edits to turn output into the reference | proxy for **post-editing effort**; lower = less human fixing. |
| **BERTScore** | higher = better | embedding (semantic) similarity, multilingual BERT | catches correct meaning with different words; 1 pt is meaningful. |
| **COMET** | higher = better | learned neural metric (`wmt22-comet-da`), uses source+output+reference | **the modern gold standard**; correlates best with human judgment. We rank by COMET. A 1–2 pt (0.01–0.02) move is meaningful. |
| **Legal-term accuracy** | higher = better | our metric: share of 26 critical legal terms rendered with the accepted standard Hindi term | concrete; ~1 pt ≈ 3 term-instances; ceilings near 95% on common terms. |

All scores are scaled 0–100 for readability (COMET/BERTScore ×100).

---

## Results (run of 2026-06-04, 500-sentence subset)

![BLEU and COMET by system](results/chart_bleu_comet.png)

Ranked by COMET (the metric that best tracks human judgment). **up = higher is
better, down = lower is better.** Full machine-readable table:
[`results/benchmark_full_metrics.md`](results/benchmark_full_metrics.md).
Regenerate the chart with `python scripts/plot_results.py` (needs `matplotlib`).

| Rank | System | Type | BLEU↑ | CHRF++↑ | METEOR↑ | TER↓ | BERTSc↑ | COMET↑ | Term%↑ | n | err |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Anuvad-gpt54mini | PRODUCT | **30.59** | **56.88** | 50.78 | **56.34** | **87.75** | **80.67** | 95.7 | 500 | 0 |
| 2 | GPT-5.4 | raw | 29.19 | 55.72 | 49.62 | 58.20 | 87.32 | 80.65 | 94.6 | 500 | 0 |
| 3 | Anuvad-gpt54 | PRODUCT | 30.42 | 56.18 | **50.79** | 56.77 | 87.49 | 80.44 | **97.0** | 500 | 0 |
| 4 | GPT-4.1 | raw | 27.37 | 53.94 | 47.88 | 60.99 | 86.54 | 80.31 | 94.6 | 500 | 0 |
| 5 | Google-Translate | raw | 27.65 | 52.47 | 46.97 | 59.04 | 86.36 | 79.94 | 90.8 | 334 | 166 |
| 6 | GPT-5.4-mini | raw | 29.14 | 55.68 | 48.92 | 58.05 | 87.19 | 79.71 | 95.5 | 389 | 111 |
| 7 | GPT-4.1-mini | raw | 24.99 | 51.31 | 45.28 | 62.65 | 85.96 | 79.42 | 90.0 | 500 | 0 |
| 8 | GPT-4o | raw | 28.15 | 53.65 | 47.84 | 60.17 | 86.74 | 79.22 | 94.0 | 500 | 0 |
| 9 | Sarvam-v1 | raw | 29.14 | 53.41 | 47.88 | 58.09 | 86.83 | 79.08 | 95.0 | 500 | 0 |
| 10 | Anuvad-sarvam | PRODUCT | 30.12 | 56.14 | 48.73 | 57.54 | 87.18 | 78.53 | 96.0 | 500 | 0 |
| 11 | GPT-4o-mini | raw | 24.12 | 50.50 | 44.85 | 64.24 | 85.81 | 78.34 | 91.0 | 500 | 0 |

### What the numbers say (and don't)

- **Anuvad-gpt54mini ranks first overall**, topping BLEU, CHRF++, BERTScore and
  COMET. On COMET it edges raw GPT-5.4 by a hair (80.67 vs 80.65) — i.e. a
  product on a *cheaper* base matches the premium raw model.
- **The product layer (glossary + post-processing) improves 6 of 7 metrics on
  every base it is applied to.** Comparing each Anuvad row to its own raw base:
  - vs raw GPT-5.4: BLEU +1.23, CHRF++ +0.46, METEOR +1.17, TER −1.43 (better),
    BERTScore +0.17, term +2.4 pts. COMET −0.21.
  - vs raw Sarvam-v1: BLEU +0.98, CHRF++ +2.73, METEOR +0.85, TER −0.55 (better),
    BERTScore +0.35, term +1.0 pt. COMET −0.55.
- **The honest exception: COMET.** On the premium and Sarvam bases the layer
  *slightly lowers* COMET (−0.2 to −0.6). Enforcing standard reference
  terminology raises overlap/term metrics but can marginally reduce a learned
  fluency metric. We report this rather than hide it. On the value base
  (gpt54mini) COMET is the highest of any system.
- **Reliability:** the Anuvad runs completed all 500 with 0 errors; two raw runs
  (GPT-5.4-mini, Google) had transient API failures and are scored on fewer
  outputs (see `n`/`err`).

No single system wins every metric; we report all seven so readers can weight
them for their own use case.

## Reproduce

```bash
# 1. Raw-model benchmark (anyone can run this with their own API keys)
pip install -r requirements.txt
bash data/fetch_dataset.sh
python scripts/benchmark_translation.py            # writes results/benchmark_<model>.json

# 2. Full metric scoring on the saved outputs (no API calls)
python scripts/score_full_metrics.py               # writes results/benchmark_full_metrics.{json,md}
```

The **Anuvad product** rows are produced by `scripts/benchmark_anuvad.py`, which
calls Vaquill's proprietary translation pipeline (glossary + post-processing) and
therefore needs Vaquill's backend and glossary database. **You cannot reproduce
the Anuvad pipeline from this repo** — but we publish **every Anuvad per-sentence
output** in `results/`, so anyone can independently re-score and audit the Anuvad
numbers with `score_full_metrics.py`. That is the honest line: the raw-model
benchmark is fully open; the product's *outputs* are open and auditable; the
product's *pipeline* is proprietary.

---

## Repo layout

```
scripts/
  benchmark_translation.py   raw-model runner (open, reproducible by anyone)
  benchmark_anuvad.py        Anuvad product runner (needs Vaquill backend; here for transparency)
  legal_term_accuracy.py     the 26-term legal-terminology checker
  score_full_metrics.py      scores ALL systems on the full metric set from saved outputs
data/
  fetch_dataset.sh           downloads the WMT25-TS dataset from upstream
  transform.md               exact stratification / cleaning steps
results/
  benchmark_<system>.json    per-sentence outputs (en, human ref, system output) for every system
  benchmark_full_metrics.{json,md}   the combined, ranked table
```

---

## Caveats (please read before citing)

- **BLEU vs glossary.** BLEU rewards matching the reference's exact wording; a
  glossary that enforces a different-but-correct standard term can leave BLEU
  flat while improving terminology. We report COMET and term accuracy precisely
  so quality is not judged on overlap alone.
- **Term-accuracy ceiling.** The 26 terms are common; strong models already score
  ~90–95%. The glossary's larger value is the long tail of specialised terms,
  which this metric under-counts.
- **API errors.** Some raw runs had transient API failures (disclosed per system
  in the `errors` / `n` columns); those systems are scored on their successful
  outputs.
- **Subset, not full set.** 500 of 5,000 sentences. A different seed shifts
  absolute scores ~1–2 BLEU but not the relative picture.
- **Automatic metrics, not human evaluation.** These correlate with, but do not
  replace, human judgment.

---

## License

Code: Apache-2.0 (see `LICENSE`). The dataset is the property of its authors
(IIT Patna) under their upstream terms; we redistribute none of it. Result files
contain our systems' outputs plus the dataset's reference sentences for scoring
transparency; if the upstream authors object to reference redistribution we will
replace references with hashes.
