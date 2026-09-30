# -*- coding: utf-8 -*-
"""
05 - Predicate-level measures (the "mechanism" variables)
=========================================================
For every transitive predicate in the cleaned dataset (step 04), compute from
its OVERT objects:

  Prototypical complement / predictability (Salimi & Rezai factor 5, RQ3)
    obj_entropy      : Shannon entropy (bits) of the object-lemma distribution,
                       Miller-Madow bias-corrected (small samples otherwise look
                       too predictable). LOWER = more predictable object.
    obj_entropy_r10  : RAREFIED entropy: mean entropy of 200 random samples of
                       exactly 10 objects. Entropy grows with sample size, so
                       frequent predicates look "less predictable" just because
                       we see more of their objects; rarefaction removes that.
                       This is the MAIN predictability measure (reliable only).
    top_obj_share    : share of the single most frequent object lemma
                       (لاک زدن -> ناخن would be close to 1).
    obj_ttr          : distinct object lemmas / overt objects.

  Genericity / indefiniteness (Salimi & Rezai factors 1-2)
    bare_rate        : share of overt objects that are bare
                       (no را, no determiner/numeral, singular, unmodified)
    no_ra_rate       : share of overt objects without را
    pron_rate        : share of overt objects that are pronouns

  Controls
    log_freq         : log of predicate frequency
    n_obj            : number of overt objects the measures rest on

Because measures resting on very few objects are noisy, a flag
`reliable` marks predicates with at least MIN_OBJ_RELIABLE overt objects;
step 07 runs the models on all predicates and on reliable ones only.

Input : outputs/tables/04_analysis_tokens.csv
Output: outputs/tables/05_predicate_measures.csv
        outputs/tables/05_analysis_tokens.csv   (tokens + predicate measures)
"""

from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path("outputs/tables")
MIN_OBJ_RELIABLE = 10

tok = pd.read_csv(OUT / "04_analysis_tokens.csv", encoding="utf-8-sig")


def entropy_mm(labels):
    """Shannon entropy in bits with the Miller-Madow correction."""
    counts = labels.value_counts().values
    n = counts.sum()
    if n == 0:
        return np.nan
    p = counts / n
    h = -(p * np.log2(p)).sum()
    return h + (len(counts) - 1) / (2 * n * np.log(2))


RNG = np.random.default_rng(2026)


def entropy_rarefied(labels, k=10, reps=200):
    """Mean plain Shannon entropy (bits) over `reps` random subsamples of size k."""
    arr = labels.to_numpy()
    if len(arr) < k:
        return np.nan
    hs = []
    for _ in range(reps):
        sub = pd.Series(RNG.choice(arr, size=k, replace=False))
        p = sub.value_counts(normalize=True).values
        hs.append(-(p * np.log2(p)).sum())
    return float(np.mean(hs))


rows = []
for pred, g in tok.groupby("predicate"):
    objs = g[g["has_obj"]]
    lem = objs["obj_lemma"].dropna()
    rows.append({
        "predicate": pred,
        "cp_strict": g["cp_strict"].iloc[0],
        "cp_broad": g["cp_broad"].iloc[0],
        "light_verb": g["light_verb"].iloc[0],
        "n": len(g),
        "n_obj": len(objs),
        "omission_rate": g["omitted"].mean(),
        "obj_entropy": entropy_mm(lem),
        "obj_entropy_r10": entropy_rarefied(lem),
        "top_obj_share": lem.value_counts(normalize=True).iloc[0] if len(lem) else np.nan,
        "top_obj": lem.value_counts().index[0] if len(lem) else None,
        "obj_ttr": lem.nunique() / len(lem) if len(lem) else np.nan,
        "bare_rate": objs["obj_bare"].astype(bool).mean(),
        "no_ra_rate": 1 - objs["obj_ra"].astype(bool).mean(),
        "pron_rate": objs["obj_pron"].astype(bool).mean(),
    })
m = pd.DataFrame(rows)
m["log_freq"] = np.log(m["n"])
m["reliable"] = m["n_obj"] >= MIN_OBJ_RELIABLE
m.to_csv(OUT / "05_predicate_measures.csv", index=False, encoding="utf-8-sig")

measures = ["obj_entropy_r10", "obj_entropy", "top_obj_share", "obj_ttr", "bare_rate",
            "no_ra_rate", "pron_rate", "log_freq"]
tok = tok.merge(m[["predicate", "reliable"] + measures], on="predicate", how="left")
tok.to_csv(OUT / "05_analysis_tokens.csv", index=False, encoding="utf-8-sig")

pd.set_option("display.width", 200)
print(f"Predicates: {len(m)}   reliable (>= {MIN_OBJ_RELIABLE} overt objects): {m['reliable'].sum()}")
print(f"Tokens covered by reliable predicates: "
      f"{tok['reliable'].sum()} of {len(tok)} ({tok['reliable'].mean():.1%})")

r = m[m["reliable"]]
print("\n=== Mean of each measure: complex vs simple (reliable predicates) ===")
print(r.groupby("cp_strict")[measures + ["omission_rate"]].mean().round(3).T
      .rename(columns={False: "simple", True: "complex"}).to_string())

print("\n=== Spearman correlation with omission rate (reliable predicates) ===")
print(r[measures + ["omission_rate"]].corr(method="spearman")["omission_rate"]
      .drop("omission_rate").round(3).to_string())

print("\n=== Correlations among the measures (check for collinearity) ===")
print(r[measures].corr(method="spearman").round(2).to_string())

print("\n=== Most predictable objects (lowest entropy, reliable) ===")
print(r.sort_values("obj_entropy_r10").head(15)
      [["predicate", "n_obj", "top_obj", "top_obj_share", "obj_entropy_r10", "omission_rate"]]
      .round(3).to_string(index=False))

print("\n=== Least predictable objects (highest entropy, reliable) ===")
print(r.sort_values("obj_entropy_r10", ascending=False).head(10)
      [["predicate", "n_obj", "top_obj", "top_obj_share", "obj_entropy_r10", "omission_rate"]]
      .round(3).to_string(index=False))

print("\nSaved: 05_predicate_measures.csv, 05_analysis_tokens.csv")
