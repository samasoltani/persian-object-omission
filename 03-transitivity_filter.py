# -*- coding: utf-8 -*-
"""
03 - Corpus-derived transitivity and the analysis dataset
=========================================================
No valency lexicon is available (yet), so a predicate counts as TRANSITIVE
if, in PerDT, it occurs with an overt object
    (a) at least MIN_OBJ times, and
    (b) in at least THRESHOLD of its uses.
Because any threshold is a choice, we report three (5%, 10%, 20%) as a
sensitivity analysis. 10% is the main setting.

Uses with a clausal complement (ccomp: «گفت که ...») are removed: there the
clause fills the object slot, so they are neither "object present" nor "omitted".

Outcome: omitted = the transitive predicate has no overt object.
Tokens whose coordinated verb carries an object (possible contextual/shared
object, e.g. «آن را باز کنند و بخوانند») are KEPT but flagged; the models in
step 06 are run with and without them.

This step gives the first DESCRIPTIVE answer to RQ1 (complex vs simple) and
RQ2 (light verb type), both per token and per predicate type.

Input : outputs/tables/02_verb_tokens.csv
Output: outputs/tables/03_predicates.csv
        outputs/tables/03_sensitivity.csv
        outputs/tables/03_analysis_tokens.csv   (main threshold, 10%)
"""

from pathlib import Path
import pandas as pd

OUT = Path("outputs/tables")
MIN_OBJ = 3            # at least 3 overt-object uses
MIN_N = 5              # at least 5 uses in total
THRESHOLDS = [0.05, 0.10, 0.20]
MAIN = 0.10

df = pd.read_csv(OUT / "02_verb_tokens.csv", encoding="utf-8-sig")
df = df[~df["has_ccomp"]].copy()                 # clause fills the object slot
df["omitted"] = ~df["has_obj"]

# ---------------------------------------------------------------------------
# Predicate-level table
# ---------------------------------------------------------------------------
pred = (df.groupby("predicate")
          .agg(n=("has_obj", "size"), n_obj=("has_obj", "sum"),
               cp_strict=("cp_strict", "first"), cp_broad=("cp_broad", "first"),
               light_verb=("light_verb", "first"))
          .reset_index())
pred["obj_rate"] = pred["n_obj"] / pred["n"]
pred["omission_rate"] = 1 - pred["obj_rate"]
for t in THRESHOLDS:
    pred[f"transitive_{int(t*100)}"] = ((pred["n_obj"] >= MIN_OBJ) & (pred["n"] >= MIN_N)
                                       & (pred["obj_rate"] >= t))
pred.sort_values("n", ascending=False).to_csv(
    OUT / "03_predicates.csv", index=False, encoding="utf-8-sig")


# ---------------------------------------------------------------------------
# Sensitivity table: RQ1 per threshold and per CP definition
# ---------------------------------------------------------------------------
def summarize(tok, types, cp_col):
    """Omission rate for complex vs simple, per token and per predicate type."""
    out = {}
    for label, is_cp in [("complex", True), ("simple", False)]:
        tk = tok[tok[cp_col] == is_cp]
        ty = types[types[cp_col] == is_cp]
        out[f"{label}_types"] = len(ty)
        out[f"{label}_tokens"] = len(tk)
        out[f"{label}_omit_token"] = round(tk["omitted"].mean(), 3)
        out[f"{label}_omit_type"] = round(ty["omission_rate"].mean(), 3)
    return out


rows = []
for t in THRESHOLDS:
    col = f"transitive_{int(t*100)}"
    keep = set(pred.loc[pred[col], "predicate"])
    tok = df[df["predicate"].isin(keep)]
    types = pred[pred[col]]
    for cp_col in ["cp_strict", "cp_broad"]:
        rows.append({"threshold": t, "cp_definition": cp_col, **summarize(tok, types, cp_col)})
sens = pd.DataFrame(rows)
sens.to_csv(OUT / "03_sensitivity.csv", index=False, encoding="utf-8-sig")

pd.set_option("display.width", 200)
print("=== RQ1 (descriptive): omission rate, complex vs simple ===")
print("   *_omit_token = share of tokens without object")
print("   *_omit_type  = mean omission rate over predicate types (each type counts once)\n")
print(sens[["threshold", "cp_definition",
            "complex_types", "simple_types",
            "complex_omit_token", "simple_omit_token",
            "complex_omit_type", "simple_omit_type"]].to_string(index=False))

# ---------------------------------------------------------------------------
# Main analysis dataset (10%)
# ---------------------------------------------------------------------------
main_col = f"transitive_{int(MAIN*100)}"
keep = set(pred.loc[pred[main_col], "predicate"])
ana = df[df["predicate"].isin(keep)].copy()
ana = ana.merge(pred[["predicate", "n", "obj_rate"]].rename(
    columns={"n": "pred_freq", "obj_rate": "pred_obj_rate"}), on="predicate")
ana.to_csv(OUT / "03_analysis_tokens.csv", index=False, encoding="utf-8-sig")

print(f"\n=== Main dataset (threshold {MAIN:.0%}) ===")
print(f"transitive predicates: {len(keep)}   tokens: {len(ana)}   "
      f"omitted: {ana['omitted'].sum()} ({ana['omitted'].mean():.1%})")
print(f"  of the omitted, conjunct has an object (possible shared object): "
      f"{(ana['omitted'] & ana['conjunct_has_obj']).sum()}")

# ---------------------------------------------------------------------------
# RQ2 (descriptive): light verb type
# ---------------------------------------------------------------------------
print("\n=== RQ2 (descriptive): omission by light verb (CP-strict, main dataset) ===")
lv = (ana[ana["cp_strict"]]
      .groupby("light_verb")
      .agg(tokens=("omitted", "size"), omit_token=("omitted", "mean"),
           predicate_types=("predicate", "nunique"))
      .query("tokens >= 50")
      .sort_values("tokens", ascending=False))
lv["omit_token"] = lv["omit_token"].round(3)
print(lv.to_string())

# ---------------------------------------------------------------------------
# Sanity check: most frequent transitive predicates and their omission rate
# ---------------------------------------------------------------------------
print("\n=== 25 most frequent transitive predicates (main dataset) ===")
top = (pred[pred[main_col]].sort_values("n", ascending=False).head(25)
       [["predicate", "n", "n_obj", "omission_rate", "cp_strict"]])
top["omission_rate"] = top["omission_rate"].round(3)
print(top.to_string(index=False))

print("\n=== Predicates with the HIGHEST omission among frequent transitives (n >= 30) ===")
hi = (pred[pred[main_col] & (pred["n"] >= 30)]
      .sort_values("omission_rate", ascending=False).head(20)
      [["predicate", "n", "n_obj", "omission_rate", "cp_strict"]])
hi["omission_rate"] = hi["omission_rate"].round(3)
print(hi.to_string(index=False))

print("\nSaved: 03_predicates.csv, 03_sensitivity.csv, 03_analysis_tokens.csv")
