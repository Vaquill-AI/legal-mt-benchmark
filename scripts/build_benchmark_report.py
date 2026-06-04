"""
Build a combined, reproducible benchmark report across all systems.

Reads every saved per-system output in output/ (raw models written by
benchmark_translation.py, and the Anuvad product written by
benchmark_anuvad.py), recomputes legal-term accuracy UNIFORMLY with the same
checker for every system, and emits:
    output/benchmark_combined.csv
    output/benchmark_combined.md

So the table is apples-to-apples: same 500 sentences, same BLEU/CHRF++,
same term checker, for raw models and the Anuvad product alike.
"""

import csv
import json
from pathlib import Path

from legal_term_accuracy import term_accuracy

OUT = Path(__file__).resolve().parents[1] / "results"
SKIP = {"benchmark_results.json", "benchmark_enrichment.json",
        "benchmark_combined.json"}


def load_systems() -> list[dict]:
    rows = []
    for f in sorted(OUT.glob("benchmark_*.json")):
        if f.name in SKIP:
            continue
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        results = data.get("results")
        metrics = data.get("metrics", {})
        if not results or "bleu" not in metrics:
            continue
        name = data.get("model", f.stem.replace("benchmark_", ""))
        is_product = name.lower().startswith("anuvad")
        term = term_accuracy(results)  # uniform checker for ALL systems
        n_pred = sum(1 for r in results if r.get("hi_pred"))
        rows.append({
            "system": name,
            "type": "PRODUCT (model+glossary)" if is_product else "raw model",
            "bleu": metrics.get("bleu"),
            "chrf_pp": metrics.get("chrf_pp"),
            "term_acc_pct": term["term_accuracy_pct"],
            "term_applicable": term["applicable"],
            "outputs_scored": n_pred,
            "errors": data.get("errors", 0),
        })
    # rank by BLEU desc
    rows.sort(key=lambda r: (-(r["bleu"] or 0)))
    return rows


def main():
    rows = load_systems()

    # CSV
    csv_path = OUT / "benchmark_combined.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Markdown
    md = []
    md.append("# WMT25 Legal EN->HI Benchmark - Combined Results\n")
    md.append("Same 500 stratified sentences (seed=42) from the WMT25 Legal "
              "Domain Test Suite (IIT Patna). Same metrics for every system.\n")
    md.append("| Rank | System | Type | BLEU | CHRF++ | LegalTerm% | Outputs | Errors |")
    md.append("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        md.append(f"| {i} | {r['system']} | {r['type']} | {r['bleu']} | "
                  f"{r['chrf_pp']} | {r['term_acc_pct']} | {r['outputs_scored']} "
                  f"| {r['errors']} |")
    md.append("\n*LegalTerm% = share of 26 critical legal terms (6 categories) "
              "rendered with the accepted standard legal-Hindi term, same "
              "checker for all systems.*\n")
    md_path = OUT / "benchmark_combined.md"
    md_path.write_text("\n".join(md))

    print("\n".join(md))
    print(f"\nWrote: {csv_path}\n       {md_path}")


if __name__ == "__main__":
    main()
