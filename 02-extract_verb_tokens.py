# -*- coding: utf-8 -*-
"""
02 - Extract one row per verb token from PerDT
==============================================
Every active lexical verb (XPOS = V_ACT) becomes one row with:
  - the PREDICATE (simple verb, or non-verbal element + light verb)
  - whether it has an overt direct object, and what that object looks like
  - the instance-level factors of Salimi & Rezai (aspect, mood, coordination ...)
  - flags for the false positives found in step 01

No transitivity filter yet: that is step 03.

Two definitions of "complex predicate" (reported side by side in the paper):
  CP-strict : the verb has a compound:lvc dependent            (e.g. لاک زد، پیدا کرد)
  CP-broad  : CP-strict  OR  an ADJ/NOUN xcomp under a light verb
              (in UD PerDT, adjectival NVEs are often xcomp: باز کرد، رها کرد، پر کرد)

Input : data/perdt/*.conllu
Output: outputs/tables/02_verb_tokens.csv
"""

from collections import Counter
from pathlib import Path
import pandas as pd
from conllu_reader import read_all

OUT = Path("outputs/tables")
OUT.mkdir(parents=True, exist_ok=True)

# light verbs used for the CP-broad definition (past-stem lemmas, as in PerDT)
LIGHT_VERBS = {"کرد", "نمود", "ساخت", "گردانید", "داد", "زد", "گرفت", "داشت",
               "آورد", "کشید", "خورد", "گذاشت", "برد", "ورزید"}
DEMONSTRATIVES = {"این", "آن", "همین", "همان"}
INDEF = {"یک", "یه"}


def is_imperfective(form):
    return form.startswith("می") or form.startswith("نمی")


def ra_marked(tok, kids):
    """True if the token carries «را/رو» as a case dependent."""
    return any(k["deprel"] == "case" and k["form"] in {"را", "رو"}
               for k in kids.get(tok["id"], []))


def is_object(tok, kids):
    """Overt direct object: deprel obj, OR an obl/obl:arg dependent marked with «را».
    PerDT sometimes tags the «را»-object of a complex predicate as obl:arg
    (e.g. «خربزه را دندان بزن»); «را» marks a direct object, so we count it."""
    if tok["deprel"] == "obj":
        return True
    return tok["deprel"].startswith("obl") and ra_marked(tok, kids)


def describe_object(obj, kids):
    """Surface properties of an overt object (used later for factors 1-2)."""
    ks = kids.get(obj["id"], [])
    ra = any(k["deprel"] == "case" and k["form"] in {"را", "رو"} for k in ks)
    pron = obj["upos"] == "PRON"
    plural = obj["feats"].get("Number") == "Plur"
    dem = any(k["deprel"] == "det" and k["lemma"] in DEMONSTRATIVES for k in ks)
    indef = any(k["lemma"] in INDEF and k["deprel"] in {"det", "nummod"} for k in ks)
    modified = any(k["deprel"] in {"amod", "nmod", "acl", "nmod:poss"} for k in ks)
    # "bare" object = generic/non-specific candidate: no را, not a pronoun,
    # no demonstrative / indefinite / numeral, singular, unmodified
    num = any(k["deprel"] == "nummod" for k in ks)
    bare = not (ra or pron or plural or dem or indef or num or modified)
    return {"obj_lemma": obj["lemma"], "obj_upos": obj["upos"], "obj_ra": ra,
            "obj_pron": pron, "obj_plural": plural, "obj_dem": dem,
            "obj_indef": indef, "obj_modified": modified, "obj_bare": bare}


rows = []
for s in read_all():
    toks = s["tokens"]
    by_id = {t["id"]: t for t in toks}
    kids = {}
    for t in toks:
        kids.setdefault(t["head"], []).append(t)

    for v in toks:
        if v["upos"] != "VERB" or v["xpos"] != "V_ACT":
            continue                      # skip passives, auxiliaries, modals
        ks = kids.get(v["id"], [])
        rels = [k["deprel"] for k in ks]

        # --- predicate -----------------------------------------------------
        lvc = [k for k in ks if k["deprel"] == "compound:lvc"]
        xnve = [k for k in ks if k["deprel"] == "xcomp" and k["upos"] in {"ADJ", "NOUN"}]
        if lvc:
            nve = lvc[0]["lemma"]
        elif xnve and v["lemma"] in LIGHT_VERBS:
            nve = xnve[0]["lemma"]
        else:
            nve = None
        cp_strict = bool(lvc)
        cp_broad = nve is not None
        predicate = f"{nve} {v['lemma']}" if nve else v["lemma"]

        # --- overt object --------------------------------------------------
        objs = [k for k in ks if is_object(k, kids)]
        objs.sort(key=lambda k: k["deprel"] != "obj")   # a true obj first
        row = {
            "file": s["file"], "sent_id": s["sent_id"], "tok_id": v["id"],
            "form": v["form"], "verb_lemma": v["lemma"], "nve": nve,
            "predicate": predicate, "cp_strict": cp_strict, "cp_broad": cp_broad,
            "light_verb": v["lemma"] if nve else None,
            "has_obj": bool(objs),
            "obj_from_obl_ra": bool(objs) and objs[0]["deprel"] != "obj",
        }
        empty_obj = {k: None for k in ["obj_lemma", "obj_upos", "obj_ra", "obj_pron",
                                       "obj_plural", "obj_dem", "obj_indef",
                                       "obj_modified", "obj_bare"]}
        row.update(describe_object(objs[0], kids) if objs else empty_obj)

        # --- instance-level factors (Salimi & Rezai 4 and 6) ---------------
        aux_lemmas = [k["lemma"] for k in ks if k["deprel"] == "aux"]
        row.update({
            "imperfective": is_imperfective(v["form"]),
            "progressive": "داشت" in aux_lemmas,       # دارد می‌خورد
            "imperative": v["feats"].get("Mood") == "Imp",
            "negated": v["feats"].get("Polarity") == "Neg",
            "tense": v["feats"].get("Tense", "-"),
        })

        # --- coordination: is a conjunct verb carrying an object? ----------
        conj_verbs = [k for k in ks if k["deprel"] == "conj" and k["upos"] == "VERB"]
        if v["deprel"] == "conj" and v["head"] in by_id:
            conj_verbs.append(by_id[v["head"]])
            conj_verbs += [k for k in kids.get(v["head"], [])
                           if k["deprel"] == "conj" and k["upos"] == "VERB" and k["id"] != v["id"]]
        row["in_coordination"] = bool(conj_verbs)
        row["conjunct_has_obj"] = any(
            any(is_object(k, kids) for k in kids.get(c["id"], [])) for c in conj_verbs)

        # --- other flags from step 01 --------------------------------------
        row.update({
            "has_ccomp": any(r.startswith("ccomp") for r in rels),
            "has_xcomp_verb": any(k["deprel"] == "xcomp" and k["upos"] == "VERB" for k in ks),
            # PP complement only (a «را»-marked obl:arg is an object, see is_object)
            "has_obl_arg": any(k["deprel"] == "obl:arg" and not ra_marked(k, kids) for k in ks),
            "has_nsubj": any(r.startswith("nsubj") for r in rels),
            "deprel": v["deprel"],
            "text": s["text"],
        })
        rows.append(row)

df = pd.DataFrame(rows)
df.to_csv(OUT / "02_verb_tokens.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"Active lexical verb tokens: {len(df)}")
print(f"Distinct predicates: {df['predicate'].nunique()}")
print(f"CP-strict: {df['cp_strict'].sum()}   CP-broad: {df['cp_broad'].sum()}")
print(f"Objects recovered from «را»-marked obl/obl:arg: {df['obj_from_obl_ra'].sum()}")
print("\nCP-broad additions (xcomp NVE), top 15:")
print(df[df["cp_broad"] & ~df["cp_strict"]]["predicate"].value_counts().head(15).to_string())

print("\nOvert object, by predicate type (raw, before transitivity filter):")
df["type"] = df["cp_strict"].map({True: "complex", False: "simple"})
print(pd.crosstab(df["type"], df["has_obj"], normalize="index").round(3))

print("\nOvert objects - surface properties:")
o = df[df["has_obj"]]
for c in ["obj_ra", "obj_pron", "obj_plural", "obj_dem", "obj_indef", "obj_modified", "obj_bare"]:
    print(f"  {c:13s} {o[c].mean():.3f}")

print("\nInstance-level factors (share of all verb tokens):")
for c in ["imperfective", "progressive", "imperative", "negated",
          "in_coordination", "conjunct_has_obj", "has_ccomp", "has_obl_arg"]:
    print(f"  {c:17s} {df[c].mean():.3f}")

print("\nWithout overt object: how many are 'suspect' (shared-object coordination,")
print("clausal/verbal complement)?")
no = df[~df["has_obj"]]
print(f"  no-obj tokens            : {len(no)}")
print(f"  conjunct has obj         : {no['conjunct_has_obj'].sum()}")
print(f"  has ccomp                : {no['has_ccomp'].sum()}")
print(f"  has verbal xcomp         : {no['has_xcomp_verb'].sum()}")

print("\nSaved:", (OUT / "02_verb_tokens.csv").resolve())
