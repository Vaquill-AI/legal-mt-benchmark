"""
Score EVERY system on the full WMT25 metric set, from saved per-sentence
outputs (no API calls). Same code, same data, same metrics for raw models and
the Anuvad product alike -> unbiased, reproducible.

Metrics (and direction):
  BLEU        higher better   sacrebleu corpus BLEU
  CHRF++      higher better   sacrebleu CHRF word_order=2
  METEOR      higher better   nltk single_meteor_score, averaged
  TER         LOWER  better   sacrebleu Translation Edit Rate
  BERTScore   higher better   bert_score F1, lang=hi (multilingual BERT)
  COMET       higher better   Unbabel/wmt22-comet-da (uses src+mt+ref)
  LegalTerm%  higher better   26 critical legal terms, accepted Hindi renderings

Run with the isolated venv:
  scripts/glossary_extraction/.venv-bench/bin/python \
    scripts/glossary_extraction/score_full_metrics.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "output"
sys.path.insert(0, str(HERE))
from legal_term_accuracy import term_accuracy  # noqa: E402

SKIP = {"benchmark_results.json", "benchmark_enrichment.json",
        "benchmark_combined.json", "benchmark_full_metrics.json"}


def load_systems():
    systems = []
    for f in sorted(OUT.glob("benchmark_*.json")):
        if f.name in SKIP:
            continue
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        results = data.get("results")
        if not results:
            continue
        name = data.get("model", f.stem.replace("benchmark_", ""))
        rows = [r for r in results if r.get("hi_pred")]
        if not rows:
            continue
        systems.append({
            "name": name,
            "is_product": name.lower().startswith("anuvad"),
            "src": [r["en"] for r in rows],
            "pred": [r["hi_pred"] for r in rows],
            "ref": [r["hi_ref"] for r in rows],
            "all_rows": results,
            "n": len(rows),
            "errors": data.get("errors", 0),
        })
    return systems


def main():
    from sacrebleu.metrics import BLEU, CHRF, TER

    systems = load_systems()
    print(f"Scoring {len(systems)} systems on full metric set...\n")

    # --- COMET (load once) ---
    comet_model = None
    try:
        from comet import download_model, load_from_checkpoint
        print("Loading COMET (Unbabel/wmt22-comet-da)...")
        comet_model = load_from_checkpoint(download_model("Unbabel/wmt22-comet-da"))
    except Exception as e:
        print(f"COMET unavailable: {str(e)[:120]}")

    # --- METEOR setup ---
    try:
        from nltk.translate.meteor_score import single_meteor_score
        meteor_ok = True
    except Exception:
        meteor_ok = False

    # --- BERTScore (load once) ---
    bert_ok = False
    try:
        from bert_score import score as bert_score_fn
        bert_ok = True
    except Exception:
        pass

    for s in systems:
        m = {}
        m["bleu"] = round(BLEU().corpus_score(s["pred"], [s["ref"]]).score, 2)
        m["chrf_pp"] = round(CHRF(word_order=2).corpus_score(s["pred"], [s["ref"]]).score, 2)
        m["ter"] = round(TER().corpus_score(s["pred"], [s["ref"]]).score, 2)

        if meteor_ok:
            scores = [single_meteor_score(r.split(), p.split())
                      for r, p in zip(s["ref"], s["pred"])]
            m["meteor"] = round(100 * sum(scores) / len(scores), 2)

        if bert_ok:
            _, _, f1 = bert_score_fn(s["pred"], s["ref"], lang="hi",
                                     verbose=False, batch_size=64)
            m["bertscore_f1"] = round(f1.mean().item() * 100, 2)

        if comet_model is not None:
            data = [{"src": src, "mt": mt, "ref": ref}
                    for src, mt, ref in zip(s["src"], s["pred"], s["ref"])]
            out = comet_model.predict(data, batch_size=64, gpus=0, progress_bar=False)
            m["comet"] = round(out.system_score * 100, 2)

        ta = term_accuracy(s["all_rows"])
        m["term_acc_pct"] = ta["term_accuracy_pct"]

        s["metrics"] = m
        print(f"  {s['name']:<22} BLEU={m['bleu']} CHRF++={m['chrf_pp']} "
              f"METEOR={m.get('meteor')} TER={m.get('ter')} "
              f"BERT={m.get('bertscore_f1')} COMET={m.get('comet')} "
              f"Term={m['term_acc_pct']}% (n={s['n']}, err={s['errors']})")

    # rank by COMET (gold standard) if available else BLEU
    key = "comet" if comet_model is not None else "bleu"
    systems.sort(key=lambda s: -(s["metrics"].get(key) or 0))

    payload = {
        "metric_directions": {
            "bleu": "higher_better", "chrf_pp": "higher_better",
            "meteor": "higher_better", "ter": "LOWER_better",
            "bertscore_f1": "higher_better", "comet": "higher_better",
            "term_acc_pct": "higher_better",
        },
        "systems": [{"system": s["name"],
                     "type": "product" if s["is_product"] else "raw_model",
                     "n_scored": s["n"], "errors": s["errors"],
                     **s["metrics"]} for s in systems],
    }
    (OUT / "benchmark_full_metrics.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2))

    # markdown
    cols = ["bleu", "chrf_pp", "meteor", "ter", "bertscore_f1", "comet", "term_acc_pct"]
    hdr = {"bleu": "BLEU up", "chrf_pp": "CHRF++ up", "meteor": "METEOR up",
           "ter": "TER down", "bertscore_f1": "BERTSc up", "comet": "COMET up",
           "term_acc_pct": "Term% up"}
    md = ["# WMT25 Legal EN->HI - Full Metric Benchmark\n",
          "Same 500 stratified sentences (seed=42), WMT25 Legal Domain Test "
          "Suite (IIT Patna). Same code/metrics for every system. "
          "**up = higher is better, down = lower is better.**\n",
          "| Rank | System | Type | " + " | ".join(hdr[c] for c in cols) + " | n | err |",
          "|---|---|---|" + "|".join(["---"] * (len(cols) + 2)) + "|"]
    for i, s in enumerate(systems, 1):
        vals = " | ".join(str(s["metrics"].get(c, "")) for c in cols)
        md.append(f"| {i} | {s['name']} | {'PRODUCT' if s['is_product'] else 'raw'} "
                  f"| {vals} | {s['n']} | {s['errors']} |")
    (OUT / "benchmark_full_metrics.md").write_text("\n".join(md))
    print("\n" + "\n".join(md))
    print(f"\nWrote: {OUT/'benchmark_full_metrics.json'} and .md")


if __name__ == "__main__":
    main()
