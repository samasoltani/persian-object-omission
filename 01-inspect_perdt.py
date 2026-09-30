# -*- coding: utf-8 -*-
"""
01 - Inspect the UD Persian PerDT treebank
==========================================
Goal: before any analysis, SEE how the phenomena we need are annotated:
  1. corpus size (sentences, tokens) per file
  2. dependency relations (esp. obj, compound:lvc, ccomp, passive)
  3. verb features (Aspect, Mood, Tense, Voice, Polarity) -> needed for factors 4 and 6
  4. complex predicates: which light verbs, which NVE + LV combinations
  5. how "را" is attached to objects
  6. pronominal object clitics (e.g. "دیدمش") and multiword tokens
  7. example sentences: transitive-looking verbs WITHOUT an overt obj

Input : data/perdt/fa_perdt-ud-{train,dev,test}.conllu
Output: printed summary + CSV files in outputs/tables/ (prefix 01_)

Run from the project root (persian-object-omission).
"""

from pathlib import Path
from collections import Counter
import pandas as pd

DATA_DIR = Path("data/perdt")
OUT_DIR = Path("outputs/tables")
OUT_DIR.mkdir(parents=True, exist_ok=True)
FILES = ["fa_perdt-ud-train.conllu", "fa_perdt-ud-dev.conllu", "fa_perdt-ud-test.conllu"]


# ---------------------------------------------------------------------------
# 1. A small CoNLL-U reader (no external library needed)
# ---------------------------------------------------------------------------
def read_conllu(path):
    """Yield sentences as dicts: {'sent_id', 'text', 'tokens': [...], 'mwt': [...]}.
    Each token is a dict with the 10 CoNLL-U columns; FEATS is parsed into a dict."""
    sent = {"sent_id": None, "text": None, "tokens": [], "mwt": []}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                if sent["tokens"]:
                    yield sent
                sent = {"sent_id": None, "text": None, "tokens": [], "mwt": []}
                continue
            if line.startswith("#"):
                if line.startswith("# sent_id"):
                    sent["sent_id"] = line.split("=", 1)[1].strip()
                elif line.startswith("# text"):
                    sent["text"] = line.split("=", 1)[1].strip()
                continue
            cols = line.split("\t")
            if "-" in cols[0]:            # multiword token line, e.g. "3-4  دیدمش"
                sent["mwt"].append((cols[0], cols[1]))
                continue
            if "." in cols[0]:            # empty node (enhanced UD) - skip
                continue
            feats = {}
            if cols[5] != "_":
                for kv in cols[5].split("|"):
                    k, v = kv.split("=", 1)
                    feats[k] = v
            sent["tokens"].append({
                "id": int(cols[0]), "form": cols[1], "lemma": cols[2], "upos": cols[3],
                "xpos": cols[4], "feats": feats, "head": int(cols[6]), "deprel": cols[7],
                "misc": cols[9],
            })
    if sent["tokens"]:
        yield sent


sentences = []
print("=== 1. Corpus size ===")
for fn in FILES:
    sents = list(read_conllu(DATA_DIR / fn))
    n_tok = sum(len(s["tokens"]) for s in sents)
    print(f"{fn:32s} sentences = {len(sents):6d}   tokens = {n_tok:7d}")
    for s in sents:
        s["file"] = fn
    sentences.extend(sents)
print(f"{'TOTAL':32s} sentences = {len(sentences):6d}   "
      f"tokens = {sum(len(s['tokens']) for s in sentences):7d}")

# ---------------------------------------------------------------------------
# 2. Dependency relations
# ---------------------------------------------------------------------------
deprels = Counter(t["deprel"] for s in sentences for t in s["tokens"])
pd.DataFrame(deprels.most_common(), columns=["deprel", "count"]).to_csv(
    OUT_DIR / "01_deprels.csv", index=False, encoding="utf-8-sig")
print("\n=== 2. Relations relevant to this study ===")
for rel in sorted(deprels):
    if rel.split(":")[0] in {"obj", "iobj", "compound", "ccomp", "xcomp",
                             "nsubj", "aux", "expl", "obl"}:
        print(f"  {rel:20s} {deprels[rel]:7d}")

# ---------------------------------------------------------------------------
# 3. Verb features
# ---------------------------------------------------------------------------
verbs = [(s, t) for s in sentences for t in s["tokens"] if t["upos"] == "VERB"]
print(f"\n=== 3. VERB tokens: {len(verbs)} ===")
feat_rows = []
for feat in ["Aspect", "Mood", "Tense", "Voice", "Polarity", "VerbForm", "Person", "Number"]:
    c = Counter(t["feats"].get(feat, "(none)") for _, t in verbs)
    print(f"  {feat:9s}: {dict(c.most_common())}")
    feat_rows += [{"feature": feat, "value": v, "count": n} for v, n in c.items()]
pd.DataFrame(feat_rows).to_csv(OUT_DIR / "01_verb_features.csv", index=False, encoding="utf-8-sig")
print("  XPOS of VERB tokens:", dict(Counter(t["xpos"] for _, t in verbs).most_common()))

# PerDT has NO 'Aspect' feature, so imperfective aspect must be derived from the
# word form: the prefix "می" / "نمی" marks imperfective (e.g. می‌خورد، نمی‌خوانم).
def is_imperfective(form):
    return form.startswith("می") or form.startswith("نمی")

c = Counter(is_imperfective(t["form"]) for _, t in verbs)
print(f"  imperfective by 'می/نمی' prefix: True = {c[True]}, False = {c[False]}")


# ---------------------------------------------------------------------------
# 4. Complex predicates: head of compound:lvc = light verb?
# ---------------------------------------------------------------------------
def children(sent, head_id):
    return [t for t in sent["tokens"] if t["head"] == head_id]


lvc_head_upos = Counter()
light_verbs = Counter()
cp_combos = Counter()
for s in sentences:
    by_id = {t["id"]: t for t in s["tokens"]}
    for t in s["tokens"]:
        if t["deprel"].startswith("compound"):
            h = by_id.get(t["head"])
            if h is None:
                continue
            lvc_head_upos[(t["deprel"], h["upos"])] += 1
            if t["deprel"] == "compound:lvc":
                light_verbs[h["lemma"]] += 1
                cp_combos[f'{t["lemma"]} {h["lemma"]}'] += 1

print("\n=== 4. Complex predicates ===")
print("  compound relation -> UPOS of its head:", dict(lvc_head_upos.most_common()))
print("  top 15 light verbs (lemma of the head of compound:lvc):")
for lv, n in light_verbs.most_common(15):
    print(f"    {lv:15s} {n:6d}")
print(f"  distinct NVE + LV combinations: {len(cp_combos)}")
print("  top 15:", cp_combos.most_common(15))
pd.DataFrame(light_verbs.most_common(), columns=["light_verb", "count"]).to_csv(
    OUT_DIR / "01_light_verbs.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(cp_combos.most_common(), columns=["complex_predicate", "count"]).to_csv(
    OUT_DIR / "01_complex_predicates.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------------------
# 5. How is "را" attached?
# ---------------------------------------------------------------------------
ra = Counter()
for s in sentences:
    by_id = {t["id"]: t for t in s["tokens"]}
    for t in s["tokens"]:
        if t["form"] in {"را", "رو"}:
            h = by_id.get(t["head"])
            ra[(t["form"], t["upos"], t["deprel"], h["deprel"] if h else "ROOT")] += 1
print("\n=== 5. 'را' tokens: (form, UPOS, deprel, deprel of its head) ===")
for k, n in ra.most_common(10):
    print(f"  {k}  {n}")

# ---------------------------------------------------------------------------
# 6. Pronominal object clitics and multiword tokens
# ---------------------------------------------------------------------------
n_mwt = sum(len(s["mwt"]) for s in sentences)
print(f"\n=== 6. Multiword tokens: {n_mwt} ===")
print("  examples:", [m for s in sentences for m in s["mwt"]][:10])
obj_pron = Counter()
for s in sentences:
    for t in s["tokens"]:
        if t["deprel"] == "obj" and t["upos"] == "PRON":
            obj_pron[(t["form"], t["feats"].get("PronType", "-"))] += 1
print("  most frequent pronominal objects (form, PronType):", obj_pron.most_common(15))

# ---------------------------------------------------------------------------
# 7. Verbs with / without an overt obj, and examples without one
# NOTE: in PerDT the verb lemma is the PAST STEM (خورد، not خوردن).
# ---------------------------------------------------------------------------
rows = []
for s in sentences:
    for t in s["tokens"]:
        if t["upos"] != "VERB":
            continue
        ch = children(s, t["id"])
        rels = [c["deprel"] for c in ch]
        nve = [c["lemma"] for c in ch if c["deprel"] == "compound:lvc"]
        rows.append({
            "file": s["file"], "sent_id": s["sent_id"],
            "verb_lemma": t["lemma"],
            "predicate": (nve[0] + " " + t["lemma"]) if nve else t["lemma"],
            "is_complex": bool(nve),
            "has_obj": "obj" in rels,
            "has_ccomp": any(r.startswith("ccomp") for r in rels),
            "voice": t["feats"].get("Voice", "-"),
            "imperfective": is_imperfective(t["form"]),
            "text": s["text"],
        })
vt = pd.DataFrame(rows)
print("\n=== 7. VERB tokens: overt obj? (raw, before any valency filter) ===")
print(pd.crosstab(vt["is_complex"], vt["has_obj"], margins=True))

top = vt["predicate"].value_counts().head(40).index
summary = (vt[vt["predicate"].isin(top)]
           .groupby("predicate")
           .agg(n=("has_obj", "size"), with_obj=("has_obj", "sum"), complex=("is_complex", "first"))
           .assign(pct_obj=lambda d: (100 * d["with_obj"] / d["n"]).round(1))
           .sort_values("n", ascending=False))
print("\n  40 most frequent predicates, % with overt obj:")
print(summary.to_string())
summary.to_csv(OUT_DIR / "01_top_predicates_obj.csv", encoding="utf-8-sig")

examples = vt[(~vt["has_obj"]) & (~vt["has_ccomp"]) & (vt["voice"] != "Pass")
              & vt["predicate"].isin(["خورد", "خواند", "نوشت", "پخت", "خرید"])]
print("\n  Examples: common transitive verbs WITHOUT overt obj (first 10):")
for _, r in examples.head(10).iterrows():
    print(f"  [{r['predicate']}] {r['text']}")
examples.to_csv(OUT_DIR / "01_examples_no_obj.csv", index=False, encoding="utf-8-sig")

print("\nDone. CSV files written to", OUT_DIR.resolve())
