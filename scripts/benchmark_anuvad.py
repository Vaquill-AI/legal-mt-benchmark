"""
NOTE: This file is published for TRANSPARENCY only.
It calls Vaquill's proprietary translation pipeline (app.services.*,
the Vidhi Shabdavali glossary database, etc.) and therefore CANNOT be
run outside Vaquill's backend. External users cannot reproduce the
Anuvad product rows from this script. They CAN, however, independently
re-score every Anuvad per-sentence output we publish in results/ using
score_full_metrics.py. See README.md ("Reproduce").
"""
"""
Anuvad PRODUCT benchmark on the WMT25 Legal Domain Test Suite (IIT Patna).

Unlike benchmark_translation.py (which tests RAW models with a simple prompt),
this runs the full Anuvad production pipeline:
    base model (gpt54 / gpt54mini / sarvam) + Vidhi Shabdavali glossary
    + legal-term/citation/date/currency post-processing.

This lets us add an "Anuvad (product)" row next to the raw-model rows, i.e.
"finished AI product vs raw LLM models" on the exact same 500 sentences and
the exact same BLEU / CHRF++ metrics.

Usage:
  python scripts/glossary_extraction/benchmark_anuvad.py --smoke 5 --engine gpt54mini
  python scripts/glossary_extraction/benchmark_anuvad.py --engine gpt54
  python scripts/glossary_extraction/benchmark_anuvad.py --engine gpt54mini
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# repo root on path + load env (Supabase glossary + OpenAI/Sarvam keys)
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
load_dotenv(BASE / ".env")

# reuse the exact dataset loader + metrics from the raw-model harness so the
# 500-sentence subset (seed=42) and scoring are identical.
sys.path.insert(0, str(BASE / "scripts" / "glossary_extraction"))
from benchmark_translation import compute_metrics, load_dataset  # noqa: E402

OUTPUT = BASE / "results"


def stamp(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


async def translate_one(service, text: str, engine: str) -> tuple[str, list]:
    from app.services.translation_service import TranslationInput

    out = await service.translate_text(
        TranslationInput(
            text=text,
            source_language="en",
            target_language="hi",
            use_glossary=True,
            engine=engine,
            user_id="benchmark",
            product="anuvad",
        ),
        save_row=False,
    )
    return out.translated_text, out.glossary_terms_applied


async def run(engine: str, smoke: int | None) -> None:
    from app.services.translation_service import get_translation_service

    # SAFETY: disable translation-memory writes so benchmark sentences never
    # land in the production TM. TM reads (lookups) still work; only writes are
    # suppressed. No production code is modified.
    import app.services.translation_service as _ts
    _ts.schedule_tm_task = lambda coro: (coro.close() if hasattr(coro, "close") else None)
    stamp("TM writes disabled for benchmark (prod TM protected)")

    dataset = load_dataset(n_small=100, n_medium=200, n_large=200)
    if smoke:
        # take a spread: a few small + medium + large
        dataset = dataset[:2] + dataset[100:100 + max(smoke - 4, 1)] + dataset[-2:]
        dataset = dataset[:smoke]
    stamp(f"Anuvad product benchmark | engine={engine} | sentences={len(dataset)}")

    service = get_translation_service()

    sem = asyncio.Semaphore(4)
    results = [None] * len(dataset)
    errors = 0
    start = time.time()

    async def worker(i, entry):
        nonlocal errors
        async with sem:
            t0 = time.time()
            try:
                pred, gloss = await translate_one(service, entry["en"], engine)
                results[i] = {
                    "id": entry["id"], "en": entry["en"], "hi_ref": entry["hi_ref"],
                    "hi_pred": pred, "word_count": entry["word_count"],
                    "latency_ms": round((time.time() - t0) * 1000),
                    "glossary_terms": len(gloss or []),
                }
            except Exception as e:  # noqa: BLE001
                errors += 1
                results[i] = {
                    "id": entry["id"], "en": entry["en"], "hi_ref": entry["hi_ref"],
                    "hi_pred": "", "word_count": entry["word_count"],
                    "latency_ms": 0, "glossary_terms": 0, "error": str(e)[:200],
                }
                if errors <= 3:
                    stamp(f"  ERROR [{i}]: {str(e)[:140]}")

    # progress ticker
    async def ticker():
        while any(r is None for r in results):
            await asyncio.sleep(15)
            done = sum(r is not None for r in results)
            stamp(f"  {done}/{len(dataset)} done | errors={errors} "
                  f"| {(time.time()-start)/60:.1f}m elapsed")

    tick = asyncio.create_task(ticker())
    await asyncio.gather(*(worker(i, e) for i, e in enumerate(dataset)))
    tick.cancel()

    model_results = {"model": f"Anuvad-{engine}", "results": results}
    metrics = compute_metrics(model_results)
    from legal_term_accuracy import term_accuracy
    term = term_accuracy(results)
    metrics["term_accuracy_pct"] = term["term_accuracy_pct"]
    metrics["term_applicable"] = term["applicable"]
    avg_gloss = sum(r["glossary_terms"] for r in results) / max(len(results), 1)

    stamp("=" * 60)
    stamp(f"ANUVAD ({engine}) | BLEU={metrics['bleu']} | CHRF++={metrics['chrf_pp']} "
          f"| TermAcc={term['term_accuracy_pct']}% (n={term['applicable']}) "
          f"| avg glossary terms/sent={avg_gloss:.1f} | errors={errors}")
    stamp("=" * 60)

    if smoke:
        for r in results:
            print("\n--- EN  :", r["en"][:160])
            print("REF :", r["hi_ref"][:160])
            print("ANUV:", r["hi_pred"][:160])
            print(f"(glossary terms applied: {r['glossary_terms']})")
    else:
        out_file = OUTPUT / f"benchmark_anuvad-{engine}.json"
        payload = {
            "model": f"Anuvad-{engine}",
            "system_type": "product (base model + Vidhi Shabdavali glossary + post-processing)",
            "config": {
                "dataset": "WMT25 Legal Domain Test Suite (IIT Patna)",
                "dataset_files": ["data/external-corpora/wmt25-legal/eng-hin-test.eng.txt",
                                  "data/external-corpora/wmt25-legal/eng-hin-test.hin.txt"],
                "subset": {"n_small": 100, "n_medium": 200, "n_large": 200, "seed": 42},
                "direction": "en->hi",
                "engine": engine,
                "use_glossary": True,
                "glossary_terms_loaded": 83355,
                "metrics": ["BLEU (sacrebleu)", "CHRF++ (sacrebleu word_order=2)",
                            "legal_term_accuracy (26 terms / 6 categories)"],
            },
            "metrics": metrics,
            "avg_glossary_terms": round(avg_gloss, 2),
            "errors": errors,
            "elapsed_min": round((time.time() - start) / 60, 1),
            "results": results,
        }
        with open(out_file, "w") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        stamp(f"saved: {out_file}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="gpt54mini",
                    choices=["gpt54", "gpt54mini", "sarvam"])
    ap.add_argument("--smoke", type=int, default=None,
                    help="run only N sentences and print them")
    args = ap.parse_args()
    asyncio.run(run(args.engine, args.smoke))


if __name__ == "__main__":
    main()
