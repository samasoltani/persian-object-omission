# -*- coding: utf-8 -*-
"""
06 - Stratified sample for manual annotation (two annotators)
=============================================================
Why: step 05 showed that the complex > simple difference comes mainly from
RARE predicates (fewer than 10 overt objects). Rare predicates are also where
parsing errors are most likely. Before any model, we must know what the
"omitted" tokens really are.

Sample: omitted tokens, stratified by
    predicate type  (complex / simple, CP-strict)  x
    frequency band  (reliable = >= 10 overt objects / rare)
    100 tokens per cell  ->  400 tokens
plus 100 tokens WITH an overt object as a control (to estimate how often a
visible object is itself a parsing error).

Each annotator gets the same Excel file and labels column `label` with ONE code:
    F  free (indefinite) omission     - no referent in context: «دائم می‌خورد»
    C  contextual omission            - referent recoverable from context /
                                        shared with a coordinated verb
    E  annotation/parsing error       - an object IS there but was not tagged obj
    N  not a transitive use           - other sense or construction
                                        (aspectual «شروع کرد به ...», idiom, PP-verb)
    ?  unsure                          - explain in `comment`

The verb is marked in the sentence as ⟦verb⟧.
Kappa between annotators is computed in step 07 from the two filled files.

Input : outputs/tables/05_analysis_tokens.csv
Output: annotation/06_sample_annotator1.xlsx
        annotation/06_sample_annotator2.xlsx
        annotation/06_sample_key.csv   (hidden strata, for analysis only)
Requires: pip install openpyxl
"""

from pathlib import Path
import pandas as pd

from conllu_reader import read_all

SEED = 2026
PER_CELL = 100
N_CONTROL = 100
OUT = Path("annotation")
OUT.mkdir(exist_ok=True)

tok = pd.read_csv("outputs/tables/05_analysis_tokens.csv", encoding="utf-8-sig")
tok["reliable"] = tok["reliable"].fillna(False).astype(bool)

# --- sentence with the verb marked -----------------------------------------
forms = {}
for s in read_all():
    forms[(s["file"], s["sent_id"])] = [(t["id"], t["form"]) for t in s["tokens"]]


def marked(row):
    words = forms[(row["file"], row["sent_id"])]
    return " ".join(f"⟦{w}⟧" if i == row["tok_id"] else w for i, w in words)


# --- stratified sample ------------------------------------------------------
parts = []
om = tok[tok["omitted"]]
for cp in [True, False]:
    for rel in [True, False]:
        cell = om[(om["cp_strict"] == cp) & (om["reliable"] == rel)]
        k = min(PER_CELL, len(cell))
        smp = cell.sample(n=k, random_state=SEED).copy()
        smp["stratum"] = f"{'complex' if cp else 'simple'}_{'reliable' if rel else 'rare'}_omitted"
        parts.append(smp)
        print(f"{smp['stratum'].iloc[0]:32s} available {len(cell):5d}   sampled {k}")

ctrl = tok[~tok["omitted"]].sample(n=N_CONTROL, random_state=SEED).copy()
ctrl["stratum"] = "control_with_object"
parts.append(ctrl)
print(f"{'control_with_object':32s} sampled {N_CONTROL}")

sample = pd.concat(parts).sample(frac=1, random_state=SEED).reset_index(drop=True)
sample["item"] = range(1, len(sample) + 1)
sample["sentence"] = sample.apply(marked, axis=1)

# --- files for annotators (strata hidden, so labels are blind) --------------
sheet = sample[["item", "predicate", "sentence"]].copy()
sheet["label"] = ""
sheet["comment"] = ""
guide = pd.DataFrame({
    "code": ["F", "C", "E", "N", "?"],
    "meaning": [
        "Free omission: no object, no referent in context (دائم می‌خورد)",
        "Contextual omission: referent recoverable from context or shared with a coordinated verb",
        "Annotation error: there IS an object in the sentence",
        "Not a transitive use: other sense / construction (شروع کرد به ...، idiom, PP-verb)",
        "Unsure: explain in comment",
    ]})
for i in [1, 2]:
    with pd.ExcelWriter(OUT / f"06_sample_annotator{i}.xlsx") as xw:
        sheet.to_excel(xw, sheet_name="items", index=False)
        guide.to_excel(xw, sheet_name="guide", index=False)

sample[["item", "stratum", "file", "sent_id", "tok_id", "predicate", "cp_strict",
        "cp_broad", "light_verb", "reliable", "has_obj", "conjunct_has_obj",
        "imperfective", "imperative"]].to_csv(OUT / "06_sample_key.csv",
                                              index=False, encoding="utf-8-sig")
print(f"\nTotal items: {len(sample)}")
print("Saved: annotation/06_sample_annotator1.xlsx, 06_sample_annotator2.xlsx, 06_sample_key.csv")
