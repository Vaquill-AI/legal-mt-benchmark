"""
WMT25 Legal Domain EN→HI Translation Benchmark
================================================
Dataset: WMT25 Legal Domain Test Suite (IIT Patna, 5000 sentences)
Subset: 500 stratified sentences (100 small + 200 medium + 200 large)

Models tested:
  - Gemini 2.5 Pro, Gemini 2.5 Flash, Gemini 2.0 Flash
  - Claude Sonnet 4.6
  - GPT-5-mini, GPT-5.4, GPT-4o
  - Sarvam translate v1

Metrics: BLEU, CHRF++, BERTScore (matching WMT25 paper methodology)

Usage:
  python benchmark_translation.py                    # Run all models
  python benchmark_translation.py Gemini-2.5-Pro     # Run one model
  python benchmark_translation.py Sarvam-v1 GPT-4o   # Run specific models
"""

import json
import os
import random
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "wmt25-legal"
OUTPUT = BASE / "results"
LOG_FILE = OUTPUT / "benchmark.log"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------------------
# Load and stratify dataset
# ---------------------------------------------------------------------------
def load_dataset(n_small=100, n_medium=200, n_large=200, seed=42):
    with open(DATA / "eng-hin-test.eng.txt") as f:
        en_lines = [l.strip() for l in f.readlines()]
    with open(DATA / "eng-hin-test.hin.txt") as f:
        hi_lines = [l.strip() for l in f.readlines()]

    small, medium, large = [], [], []
    for i, (en, hi) in enumerate(zip(en_lines, hi_lines)):
        wc = len(en.split())
        entry = {"id": i, "en": en, "hi_ref": hi, "word_count": wc}
        if 5 <= wc <= 15:
            small.append(entry)
        elif 16 <= wc <= 35:
            medium.append(entry)
        elif 36 <= wc <= 54:
            large.append(entry)

    random.seed(seed)
    selected = (
        random.sample(small, min(n_small, len(small)))
        + random.sample(medium, min(n_medium, len(medium)))
        + random.sample(large, min(n_large, len(large)))
    )
    return selected


# ---------------------------------------------------------------------------
# Translation functions
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are a legal translation expert. Translate the following English legal text "
    "to Hindi. Use formal legal Hindi register. "
    "Preserve all legal terminology, section numbers, case citations, and proper nouns. "
    "Output ONLY the Hindi translation, nothing else."
)


def translate_gemini(text, model_id):
    from google import genai
    from google.genai import types
    # Use the AI Studio key that has Generative Language API enabled
    client = genai.Client(api_key=os.environ.get("GOOGLE_AI_STUDIO_KEY", os.environ.get("GOOGLE_API_KEY")))
    resp = client.models.generate_content(
        model=model_id,
        contents=text,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,
            max_output_tokens=2000,
        ),
    )
    text = resp.text or ""
    in_tok = resp.usage_metadata.prompt_token_count if resp.usage_metadata else 0
    out_tok = resp.usage_metadata.candidates_token_count if resp.usage_metadata else 0
    # Gemini sometimes returns explanations. Extract just the Hindi.
    # If response has multiple lines, take only lines with Devanagari
    lines = text.strip().split("\n")
    hindi_lines = [l.strip() for l in lines if any('\u0900' <= c <= '\u097F' for c in l)]
    result = " ".join(hindi_lines) if hindi_lines else text.strip()
    return result, in_tok, out_tok


def translate_openai(text, model_id):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    # GPT-5 family uses max_completion_tokens, older models use max_tokens
    is_reasoning = "gpt-5" in model_id or "o1" in model_id or "o3" in model_id
    kwargs = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    }
    if is_reasoning:
        kwargs["max_completion_tokens"] = 2000
    else:
        kwargs["temperature"] = 0
        kwargs["max_tokens"] = 2000
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content.strip(), resp.usage.prompt_tokens, resp.usage.completion_tokens


def translate_claude(text, model_id):
    from anthropic import Anthropic
    client = Anthropic()
    resp = client.messages.create(
        model=model_id,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    return resp.content[0].text.strip(), resp.usage.input_tokens, resp.usage.output_tokens


def translate_google(text):
    import httpx
    key = os.environ.get("GOOGLE_TRANSLATE_API_KEY", "")
    resp = httpx.post(
        f"https://translation.googleapis.com/language/translate/v2?key={key}",
        json={"q": text, "source": "en", "target": "hi", "format": "text"},
        timeout=15,
    )
    if resp.status_code == 200:
        translated = resp.json()["data"]["translations"][0]["translatedText"]
        return translated, len(text.split()), len(translated.split())
    raise Exception(f"Google Translate {resp.status_code}: {resp.text[:200]}")


def translate_sarvam(text):
    import httpx
    resp = httpx.post(
        "https://api.sarvam.ai/translate",
        headers={
            "api-subscription-key": os.environ["SARVAM_API_KEY"],
            "Content-Type": "application/json",
        },
        json={
            "input": text[:2000],
            "source_language_code": "en-IN",
            "target_language_code": "hi-IN",
            "model": "sarvam-translate:v1",
            "mode": "formal",
        },
        timeout=30,
    )
    if resp.status_code == 200:
        return resp.json().get("translated_text", ""), len(text.split()), len(text.split())
    raise Exception(f"Sarvam {resp.status_code}: {resp.text[:200]}")


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------
MODELS = {
    "Gemini-2.5-Pro": {
        "fn": lambda t: translate_gemini(t, "gemini-2.5-pro"),
        "cost_per_m": (1.25, 10.00),
        "provider": "google",
    },
    "Gemini-2.5-Flash": {
        "fn": lambda t: translate_gemini(t, "gemini-2.5-flash"),
        "cost_per_m": (0.15, 0.60),
        "provider": "google",
    },
    "Gemini-2.0-Flash": {
        "fn": lambda t: translate_gemini(t, "gemini-2.0-flash"),
        "cost_per_m": (0.10, 0.40),
        "provider": "google",
    },
    "GPT-4o": {
        "fn": lambda t: translate_openai(t, "gpt-4o"),
        "cost_per_m": (2.50, 10.00),
        "provider": "openai",
    },
    "GPT-4o-mini": {
        "fn": lambda t: translate_openai(t, "gpt-4o-mini"),
        "cost_per_m": (0.15, 0.60),
        "provider": "openai",
    },
    "GPT-4.1": {
        "fn": lambda t: translate_openai(t, "gpt-4.1"),
        "cost_per_m": (2.00, 8.00),
        "provider": "openai",
    },
    "GPT-4.1-mini": {
        "fn": lambda t: translate_openai(t, "gpt-4.1-mini"),
        "cost_per_m": (0.40, 1.60),
        "provider": "openai",
    },
    "GPT-5.4": {
        "fn": lambda t: translate_openai(t, "gpt-5.4"),
        "cost_per_m": (2.50, 15.00),
        "provider": "openai",
    },
    "GPT-5.4-mini": {
        "fn": lambda t: translate_openai(t, "gpt-5.4-mini"),
        "cost_per_m": (0.75, 4.50),
        "provider": "openai",
    },
    "Sarvam-v1": {
        "fn": lambda t: translate_sarvam(t),
        "cost_per_m": (0, 0),
        "provider": "sarvam",
        "cost_per_10k_chars": 0.237,
    },
    "Google-Translate": {
        "fn": lambda t: translate_google(t),
        "cost_per_m": (0, 0),
        "provider": "google_translate",
        "cost_per_10k_chars": 0.200,
    },
}


# ---------------------------------------------------------------------------
# Run benchmark for one model
# ---------------------------------------------------------------------------
def benchmark_model(model_name, model_config, dataset):
    log(f"\n{'='*60}")
    log(f"BENCHMARKING: {model_name}")
    log(f"{'='*60}")

    fn = model_config["fn"]
    results = []
    total_in_tok = 0
    total_out_tok = 0
    total_chars = 0
    errors = 0
    start = time.time()

    for i, entry in enumerate(dataset):
        try:
            t0 = time.time()
            translated, in_tok, out_tok = fn(entry["en"])
            latency = time.time() - t0

            results.append({
                "id": entry["id"],
                "en": entry["en"],
                "hi_ref": entry["hi_ref"],
                "hi_pred": translated,
                "word_count": entry["word_count"],
                "latency_ms": round(latency * 1000),
                "in_tokens": in_tok,
                "out_tokens": out_tok,
            })
            total_in_tok += in_tok or 0
            total_out_tok += out_tok or 0
            total_chars += len(entry["en"])

        except Exception as e:
            errors += 1
            results.append({
                "id": entry["id"],
                "en": entry["en"],
                "hi_ref": entry["hi_ref"],
                "hi_pred": "",
                "word_count": entry["word_count"],
                "latency_ms": 0,
                "in_tokens": 0,
                "out_tokens": 0,
                "error": str(e)[:200],
            })
            if errors <= 3:
                log(f"  ERROR [{i+1}]: {str(e)[:100]}")

        # Rate limit: small sleep to avoid 429s
        time.sleep(0.1)

        if (i + 1) % 50 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            remaining = (len(dataset) - i - 1) / rate
            log(f"  {i+1}/{len(dataset)} | {rate:.1f} sent/s | ~{remaining/60:.1f}m left | errors={errors}")

    elapsed = time.time() - start

    # Calculate cost
    if model_config["provider"] == "sarvam":
        cost = total_chars / 10000 * model_config.get("cost_per_10k_chars", 0.237)
    else:
        in_rate, out_rate = model_config["cost_per_m"]
        cost = (total_in_tok * in_rate + total_out_tok * out_rate) / 1_000_000

    latencies = [r["latency_ms"] for r in results if r["latency_ms"] > 0]
    avg_latency = sum(latencies) / max(len(latencies), 1)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    log(f"  DONE: {len(results)} in {elapsed:.0f}s | Cost: ${cost:.4f} | Avg latency: {avg_latency:.0f}ms | Errors: {errors}")

    return {
        "model": model_name,
        "provider": model_config["provider"],
        "results": results,
        "elapsed_s": round(elapsed, 1),
        "cost_usd": round(cost, 4),
        "total_in_tokens": total_in_tok,
        "total_out_tokens": total_out_tok,
        "total_chars": total_chars,
        "avg_latency_ms": round(avg_latency),
        "p95_latency_ms": p95_latency,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Compute metrics
# ---------------------------------------------------------------------------
def compute_metrics(model_results):
    from sacrebleu.metrics import BLEU, CHRF

    refs = [r["hi_ref"] for r in model_results["results"] if r.get("hi_pred")]
    preds = [r["hi_pred"] for r in model_results["results"] if r.get("hi_pred")]

    if not preds:
        return {"bleu": 0, "chrf_pp": 0}

    bleu = BLEU().corpus_score(preds, [refs])
    chrf = CHRF(word_order=2).corpus_score(preds, [refs])

    metrics = {
        "bleu": round(bleu.score, 2),
        "chrf_pp": round(chrf.score, 2),
    }

    # BERTScore
    try:
        from bert_score import score as bert_score_fn
        log(f"  Computing BERTScore ({len(preds)} predictions)...")
        P, R, F1 = bert_score_fn(preds, refs, lang="hi", verbose=False, batch_size=64)
        metrics["bertscore_f1"] = round(F1.mean().item() * 100, 2)
    except ImportError:
        log("  bert_score not installed, skipping")
        metrics["bertscore_f1"] = None

    # BLEU by sentence length bucket
    for label, lo, hi in [("small", 5, 15), ("medium", 16, 35), ("large", 36, 54)]:
        bucket_refs = [r["hi_ref"] for r in model_results["results"] if r.get("hi_pred") and lo <= r["word_count"] <= hi]
        bucket_preds = [r["hi_pred"] for r in model_results["results"] if r.get("hi_pred") and lo <= r["word_count"] <= hi]
        if bucket_preds:
            metrics[f"bleu_{label}"] = round(BLEU().corpus_score(bucket_preds, [bucket_refs]).score, 2)

    return metrics


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    open(LOG_FILE, "w").close()
    log("=" * 60)
    log("WMT25 Legal EN->HI Translation Benchmark")
    log("Dataset: WMT25 Legal Domain Test Suite (IIT Patna)")
    log("=" * 60)

    # Install deps
    try:
        import sacrebleu
    except ImportError:
        os.system("pip install -q sacrebleu")

    # Load dataset
    dataset = load_dataset(n_small=100, n_medium=200, n_large=200)
    log(f"Loaded {len(dataset)} sentences (100 small + 200 medium + 200 large)")

    # Select models
    models_to_run = list(MODELS.keys())
    if len(sys.argv) > 1:
        models_to_run = [m for m in sys.argv[1:] if m in MODELS]
        if not models_to_run:
            print(f"Available models: {', '.join(MODELS.keys())}")
            sys.exit(1)
    log(f"Models: {', '.join(models_to_run)}")

    # Run benchmarks
    all_results = {}

    # Load existing results if resuming
    results_file = OUTPUT / "benchmark_results.json"
    if results_file.exists():
        with open(results_file) as f:
            all_results = json.load(f)
        log(f"Loaded existing results for: {', '.join(all_results.keys())}")

    for model_name in models_to_run:
        if model_name in all_results:
            log(f"\nSkipping {model_name} (already benchmarked). Delete benchmark_results.json to re-run.")
            continue

        result = benchmark_model(model_name, MODELS[model_name], dataset)

        log(f"  Computing metrics for {model_name}...")
        metrics = compute_metrics(result)
        result["metrics"] = metrics
        log(f"  BLEU={metrics['bleu']} | CHRF++={metrics['chrf_pp']} | BERTScore={metrics.get('bertscore_f1', 'N/A')}")

        all_results[model_name] = result

        # Save after each model (resume-safe)
        with open(results_file, "w") as f:
            # Don't save individual results (too large), save summary
            summary = {}
            for name, r in all_results.items():
                summary[name] = {
                    "model": r["model"],
                    "provider": r["provider"],
                    "metrics": r["metrics"],
                    "cost_usd": r["cost_usd"],
                    "avg_latency_ms": r["avg_latency_ms"],
                    "p95_latency_ms": r["p95_latency_ms"],
                    "errors": r["errors"],
                    "elapsed_s": r["elapsed_s"],
                    "total_in_tokens": r["total_in_tokens"],
                    "total_out_tokens": r["total_out_tokens"],
                }
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # Save full results per model (for debugging)
        per_model_file = OUTPUT / f"benchmark_{model_name.lower().replace(' ', '_')}.json"
        with open(per_model_file, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    # Final comparison table
    log("\n" + "=" * 80)
    log("FINAL RESULTS - WMT25 Legal EN->HI (500 sentences)")
    log("=" * 80)
    log(f"{'Rank':<5} {'Model':<25} {'BLEU':>7} {'CHRF++':>8} {'BERT':>7} {'Cost':>9} {'Latency':>9} {'Errors':>7}")
    log("-" * 80)

    ranked = sorted(all_results.keys(), key=lambda x: -all_results[x]["metrics"]["bleu"])
    for rank, name in enumerate(ranked, 1):
        r = all_results[name]
        m = r["metrics"]
        bert = f"{m['bertscore_f1']:.1f}" if m.get("bertscore_f1") else "N/A"
        log(f"{rank:<5} {name:<25} {m['bleu']:>7.2f} {m['chrf_pp']:>8.2f} {bert:>7} ${r['cost_usd']:>8.4f} {r['avg_latency_ms']:>7}ms {r['errors']:>7}")

    # BLEU by sentence length
    log(f"\n{'Model':<25} {'Small':>8} {'Medium':>8} {'Large':>8}")
    log("-" * 55)
    for name in ranked:
        m = all_results[name]["metrics"]
        s = m.get("bleu_small", "N/A")
        med = m.get("bleu_medium", "N/A")
        l = m.get("bleu_large", "N/A")
        s_str = f"{s:>8.2f}" if isinstance(s, (int, float)) else f"{s:>8}"
        m_str = f"{med:>8.2f}" if isinstance(med, (int, float)) else f"{med:>8}"
        l_str = f"{l:>8.2f}" if isinstance(l, (int, float)) else f"{l:>8}"
        log(f"{name:<25} {s_str} {m_str} {l_str}")

    log(f"\nResults: {results_file}")
    log("Done.")


if __name__ == "__main__":
    main()
