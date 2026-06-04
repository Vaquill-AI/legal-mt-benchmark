# WMT25 Legal EN->HI - Full Metric Benchmark

Same 500 stratified sentences (seed=42), WMT25 Legal Domain Test Suite (IIT Patna). Same code/metrics for every system. **up = higher is better, down = lower is better.**

| Rank | System | Type | BLEU up | CHRF++ up | METEOR up | TER down | BERTSc up | COMET up | Term% up | n | err |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Anuvad-gpt54mini | PRODUCT | 30.59 | 56.88 | 50.78 | 56.34 | 87.75 | 80.67 | 95.7 | 500 | 0 |
| 2 | GPT-5.4 | raw | 29.19 | 55.72 | 49.62 | 58.2 | 87.32 | 80.65 | 94.6 | 500 | 0 |
| 3 | Anuvad-gpt54 | PRODUCT | 30.42 | 56.18 | 50.79 | 56.77 | 87.49 | 80.44 | 97.0 | 500 | 0 |
| 4 | GPT-4.1 | raw | 27.37 | 53.94 | 47.88 | 60.99 | 86.54 | 80.31 | 94.6 | 500 | 0 |
| 5 | Google-Translate | raw | 27.65 | 52.47 | 46.97 | 59.04 | 86.36 | 79.94 | 90.8 | 334 | 166 |
| 6 | GPT-5.4-mini | raw | 29.14 | 55.68 | 48.92 | 58.05 | 87.19 | 79.71 | 95.5 | 389 | 111 |
| 7 | GPT-4.1-mini | raw | 24.99 | 51.31 | 45.28 | 62.65 | 85.96 | 79.42 | 90.0 | 500 | 0 |
| 8 | GPT-4o | raw | 28.15 | 53.65 | 47.84 | 60.17 | 86.74 | 79.22 | 94.0 | 500 | 0 |
| 9 | Sarvam-v1 | raw | 29.14 | 53.41 | 47.88 | 58.09 | 86.83 | 79.08 | 95.0 | 500 | 0 |
| 10 | Anuvad-sarvam | PRODUCT | 30.12 | 56.14 | 48.73 | 57.54 | 87.18 | 78.53 | 96.0 | 500 | 0 |
| 11 | GPT-4o-mini | raw | 24.12 | 50.5 | 44.85 | 64.24 | 85.81 | 78.34 | 91.0 | 500 | 0 |