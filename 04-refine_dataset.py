# -*- coding: utf-8 -*-
"""
04 - Refine the dataset: remove structural false positives
==========================================================
Step 03 showed that many "omissions" are not omissions at all:
  (a) RELATIVE CLAUSES  «هر چه می‌خواهید بگویید»: the object is the relativized
      head noun, so the verb has no obj dependent (deprel acl / acl:relcl).
  (b) DIRECT SPEECH     «گفت: ...»: the quote fills the object slot (parataxis).
  (c) CLAUSAL / PREDICATIVE COMPLEMENTS  (ccomp, xcomp, csubj).
  (d) PP-VERBS          «به ... پرداخت»، «به ... نگاه کرد»، «به ... گوش داد»:
      the argument is a prepositional phrase (obl:arg), not a direct object.
      A predicate is treated as a PP-verb if it takes obl:arg MORE often than an
      overt object AND has an overt object in less than half of its uses
      (so a clearly transitive verb like «ریخت» is not removed).

Rules (a)-(c) remove TOKENS; rule (d) removes PREDICATES.
Then transitivity is recomputed exactly as in step 03 (5 / 10 / 20 %).
Every rule is counted, so the paper can report an exclusion flow.

Input : outputs/tables/02_verb_tokens.csv  +  data/perdt (for extra flags)
Output: outputs/tables/04_exclusions.csv
        outputs/tables/04_predicates.csv
        outputs/tables/04_sensitivity.csv
        outputs/tables/04_analysis_tokens.csv   (main threshold, 10%)
"""

from pathlib import Path
import pandas as pd
from conllu_reader import read_all

OUT = Path("outputs/tables")
MIN_OBJ, MIN_N = 3, 5
THRESHOLDS = [0.05, 0.10, 0.20]
MAIN = 0.10

df = pd.read_csv(OUT / "02_verb_tokens.csv", encoding="utf-8-sig")

# ---------------------------------------------------------------------------
# Extra token flags from the treebank (not stored in step 02)
# ---------------------------------------------------------------------------
extra = {}
for s in read_all():
    kids = {}
    for t in s["tokens"]:
        kids.setdefault(t["head"], []).append(t)
    for v in s["tokens"]:
        if v["upos"] == "VERB" and v["xpos"] == "V_ACT":
            rels = {k["deprel"] for k in kids.get(v["id"], [])}
            extra[(s["file"], s["sent_id"], v["id"])] = {
                "has_parataxis": any(r.startswith("parataxis") for r in rels),
                "has_xcomp_any": any(r == "xcomp" for r in rels),
                "has_csubj": any(r.startswith("csubj") for r in rels),
            }
ex = pd.DataFrame([{"file": k[0], "sent_id": k[1], "tok_id": k[2], **v} for k, v in extra.items()])
df = df.merge(ex, on=["file", "sent_id", "tok_id"], how="left")

# xcomp that IS the non-verbal element of a CP-broad predicate is not a complement
df["xcomp_complement"] = df["has_xcomp_any"] & ~(df["cp_broad"] & ~df["cp_strict"])
df["omitted"] = ~df["has_obj"]

# ---------------------------------------------------------------------------
# Token-level exclusions (applied in order, so each token is counted once)
# ---------------------------------------------------------------------------
rules = [
    ("relative clause (acl)", df["deprel"].str.startswith("acl")),
    ("clausal complement (ccomp)", df["has_ccomp"]),
    ("direct speech (parataxis)", df["has_parataxis"]),
    ("predicative/clausal xcomp", df["xcomp_complement"]),
    ("clausal subject (csubj)", df["has_csubj"]),
]
flow = [{"step": "active lexical verbs (step 02)", "removed": 0, "remaining": len(df)}]
keep = pd.Series(True, index=df.index)
for name, mask in rules:
    newly = keep & mask
    keep &= ~mask
    flow.append({"step": name, "removed": int(newly.sum()), "remaining": int(keep.sum())})
tok = df[keep].copy()

# ---------------------------------------------------------------------------
# Predicate table + PP-verb rule
# ---------------------------------------------------------------------------
pred = (tok.groupby("predicate")
           .agg(n=("has_obj", "size"), n_obj=("has_obj", "sum"),
                n_oblarg=("has_obl_arg", "sum"),
                cp_strict=("cp_strict", "first"), cp_broad=("cp_broad", "first"),
                light_verb=("light_verb", "first"))
           .reset_index())
pred["obj_rate"] = pred["n_obj"] / pred["n"]
pred["oblarg_rate"] = pred["n_oblarg"] / pred["n"]
pred["omission_rate"] = 1 - pred["obj_rate"]
pred["pp_verb"] = (pred["oblarg_rate"] > pred["obj_rate"]) & (pred["obj_rate"] < 0.5)
for t in THRESHOLDS:
    pred[f"transitive_{int(t*100)}"] = (~pred["pp_verb"] & (pred["n_obj"] >= MIN_OBJ)
                                       & (pred["n"] >= MIN_N) & (pred["obj_rate"] >= t))
pred.sort_values("n", ascending=False).to_csv(OUT / "04_predicates.csv",
                                              index=False, encoding="utf-8-sig")

main_col = f"transitive_{int(MAIN*100)}"
pp_removed = tok["predicate"].isin(set(pred.loc[pred["pp_verb"], "predicate"]))
flow.append({"step": "PP-verbs (obl:arg > obj, obj < 50%)", "removed": int(pp_removed.sum()),
             "remaining": int((~pp_removed).sum())})
trans_keep = tok["predicate"].isin(set(pred.loc[pred[main_col], "predicate"]))
flow.append({"step": f"not transitive at {MAIN:.0%} (or too rare)",
             "removed": int((~pp_removed & ~trans_keep).sum()),
             "remaining": int(trans_keep.sum())})
flow = pd.DataFrame(flow)
flow.to_csv(OUT / "04_exclusions.csv", index=False, encoding="utf-8-sig")
print("=== Exclusion flow ===")
print(flow.to_string(index=False))


# ---------------------------------------------------------------------------
# Sensitivity (same as step 03, on the cleaned data)
# ---------------------------------------------------------------------------
def summarize(tk_all, types_all, cp_col):
    out = {}
    for label, is_cp in [("complex", True), ("simple", False)]:
        tk = tk_all[tk_all[cp_col] == is_cp]
        ty = types_all[types_all[cp_col] == is_cp]
        out[f"{label}_types"] = len(ty)
        out[f"{label}_tokens"] = len(tk)
        out[f"{label}_omit_token"] = round(tk["omitted"].mean(), 3)
        out[f"{label}_omit_type"] = round(ty["omission_rate"].mean(), 3)
    return out


rows = []
for t in THRESHOLDS:
    col = f"transitive_{int(t*100)}"
    ks = set(pred.loc[pred[col], "predicate"])
    for cp_col in ["cp_strict", "cp_broad"]:
        rows.append({"threshold": t, "cp_definition": cp_col,
                     **summarize(tok[tok["predicate"].isin(ks)], pred[pred[col]], cp_col)})
sens = pd.DataFrame(rows)
sens.to_csv(OUT / "04_sensitivity.csv", index=False, encoding="utf-8-sig")
pd.set_option("display.width", 200)
print("\n=== RQ1 (descriptive, cleaned): omission rate, complex vs simple ===")
print(sens[["threshold", "cp_definition", "complex_types", "simple_types",
            "complex_omit_token", "simple_omit_token",
            "complex_omit_type", "simple_omit_type"]].to_string(index=False))

# ---------------------------------------------------------------------------
# Main dataset
# ---------------------------------------------------------------------------
ana = tok[trans_keep].copy()
ana = ana.merge(pred[["predicate", "n", "obj_rate"]].rename(
    columns={"n": "pred_freq", "obj_rate": "pred_obj_rate"}), on="predicate")
ana.to_csv(OUT / "04_analysis_tokens.csv", index=False, encoding="utf-8-sig")
print(f"\n=== Main dataset ({MAIN:.0%}) ===")
print(f"predicates: {ana['predicate'].nunique()}   tokens: {len(ana)}   "
      f"omitted: {ana['omitted'].sum()} ({ana['omitted'].mean():.1%})")
print(f"  omitted with an object-bearing conjunct (possible shared object): "
      f"{(ana['omitted'] & ana['conjunct_has_obj']).sum()}")

print("\n=== RQ2 (descriptive, cleaned): omission by light verb (CP-strict) ===")
lv = (ana[ana["cp_strict"]].groupby("light_verb")
      .agg(tokens=("omitted", "size"), omit_token=("omitted", "mean"),
           predicate_types=("predicate", "nunique"))
      .query("tokens >= 50").sort_values("tokens", ascending=False))
lv["omit_token"] = lv["omit_token"].round(3)
print(lv.to_string())

print("\n=== PP-verbs removed (most frequent 15) ===")
print(pred[pred["pp_verb"]].sort_values("n", ascending=False).head(15)
      [["predicate", "n", "n_obj", "n_oblarg"]].to_string(index=False))

print("\n=== Highest omission among frequent transitives after cleaning (n >= 30) ===")
hi = (pred[pred[main_col] & (pred["n"] >= 30)]
      .sort_values("omission_rate", ascending=False).head(20)
      [["predicate", "n", "n_obj", "omission_rate", "cp_strict"]])
hi["omission_rate"] = hi["omission_rate"].round(3)
print(hi.to_string(index=False))

print("\nSaved: 04_exclusions.csv, 04_predicates.csv, 04_sensitivity.csv, 04_analysis_tokens.csv")
