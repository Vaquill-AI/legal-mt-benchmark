"""
Legal-term accuracy for EN->HI legal translation.

Fixed set of 26 critical legal terms across 6 categories, each mapped to the
accepted standard legal-Hindi renderings (tatsama / court-standard). For every
sentence where the English term appears in the source, we check whether the
model output contains ANY accepted Hindi rendering. Score = hits / applicable.

The SAME checker is applied to every system (raw models AND the Anuvad product),
so the comparison is fair. This is an indicative substring-based metric, not a
human evaluation; it rewards using the correct standard legal term.
"""

import re

# 26 terms, 6 categories. Each English term -> list of accepted Hindi variants.
LEGAL_TERMS: dict[str, dict] = {
    # --- Court names ---
    "supreme court": {"cat": "court", "hi": ["उच्चतम न्यायालय", "सर्वोच्च न्यायालय"]},
    "high court": {"cat": "court", "hi": ["उच्च न्यायालय"]},
    "trial court": {"cat": "court", "hi": ["विचारण न्यायालय", "विचारणालय"]},
    "district court": {"cat": "court", "hi": ["जिला न्यायालय", "ज़िला न्यायालय"]},
    # --- Party designations ---
    "petitioner": {"cat": "party", "hi": ["याचिकाकर्ता", "याचीकर्ता"]},
    "respondent": {"cat": "party", "hi": ["प्रत्यर्थी", "उत्तरदाता", "प्रतिवादी"]},
    "appellant": {"cat": "party", "hi": ["अपीलकर्ता", "अपीलार्थी"]},
    "accused": {"cat": "party", "hi": ["अभियुक्त", "आरोपी"]},
    "complainant": {"cat": "party", "hi": ["परिवादी", "शिकायतकर्ता", "शिकायतकर्ता"]},
    "plaintiff": {"cat": "party", "hi": ["वादी"]},
    # --- Procedural terms ---
    "bail": {"cat": "procedural", "hi": ["जमानत", "ज़मानत"]},
    "petition": {"cat": "procedural", "hi": ["याचिका"]},
    "appeal": {"cat": "procedural", "hi": ["अपील"]},
    "judgment": {"cat": "procedural", "hi": ["निर्णय", "निर्णीत"]},
    "decree": {"cat": "procedural", "hi": ["डिक्री", "आज्ञप्ति"]},
    "affidavit": {"cat": "procedural", "hi": ["शपथपत्र", "शपथ पत्र", "हलफनामा"]},
    # --- Criminal law ---
    "acquittal": {"cat": "criminal", "hi": ["दोषमुक्ति", "दोषमुक्त"]},
    "conviction": {"cat": "criminal", "hi": ["दोषसिद्धि", "दोषसिद्ध"]},
    "charge sheet": {"cat": "criminal", "hi": ["आरोप पत्र", "आरोपपत्र"]},
    "cognizance": {"cat": "criminal", "hi": ["संज्ञान"]},
    # --- Evidence ---
    "witness": {"cat": "evidence", "hi": ["साक्षी", "गवाह"]},
    "evidence": {"cat": "evidence", "hi": ["साक्ष्य", "सबूत"]},
    "cross-examination": {"cat": "evidence", "hi": ["प्रतिपरीक्षा", "जिरह"]},
    # --- Statute references ---
    "section": {"cat": "statute", "hi": ["धारा"]},
    "act": {"cat": "statute", "hi": ["अधिनियम"]},
    "offence": {"cat": "statute", "hi": ["अपराध"]},
}


def term_accuracy(pairs: list[dict]) -> dict:
    """pairs: list of {"en": source, "hi_pred": output}. Returns metrics."""
    applicable = 0
    hits = 0
    by_cat: dict[str, list[int]] = {}
    for term, info in LEGAL_TERMS.items():
        pat = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
        cat = info["cat"]
        by_cat.setdefault(cat, [0, 0])  # [hits, applicable]
        for p in pairs:
            if not p.get("hi_pred"):
                continue
            if pat.search(p["en"]):
                applicable += 1
                by_cat[cat][1] += 1
                if any(v in p["hi_pred"] for v in info["hi"]):
                    hits += 1
                    by_cat[cat][0] += 1
    return {
        "term_accuracy_pct": round(100 * hits / applicable, 1) if applicable else None,
        "applicable": applicable,
        "hits": hits,
        "by_category": {c: round(100 * h / a, 1) if a else None
                        for c, (h, a) in by_cat.items()},
    }


if __name__ == "__main__":
    # Validate against saved raw-model outputs (no API calls).
    import json
    from pathlib import Path

    OUT = Path(__file__).resolve().parents[1] / "results"
    files = sorted(OUT.glob("benchmark_*.json"))
    rows = []
    for f in files:
        if f.name in ("benchmark_results.json", "benchmark_enrichment.json"):
            continue
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        results = data.get("results")
        if not results:
            continue
        name = data.get("model", f.stem.replace("benchmark_", ""))
        m = term_accuracy(results)
        if m["term_accuracy_pct"] is not None:
            rows.append((name, m["term_accuracy_pct"], m["applicable"], m["hits"]))

    rows.sort(key=lambda r: -r[1])
    print(f"{'System':<22} {'TermAcc%':>9} {'Applic':>7} {'Hits':>6}")
    print("-" * 48)
    for name, acc, app, hits in rows:
        print(f"{name:<22} {acc:>9} {app:>7} {hits:>6}")
