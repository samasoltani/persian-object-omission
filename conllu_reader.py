# -*- coding: utf-8 -*-
"""
Shared CoNLL-U reader for the project (imported by the numbered scripts).
Not a step of its own; it has no number.
"""

from pathlib import Path

DATA_DIR = Path("data/perdt")
FILES = ["fa_perdt-ud-train.conllu", "fa_perdt-ud-dev.conllu", "fa_perdt-ud-test.conllu"]


def read_conllu(path):
    """Yield sentences as dicts: {'sent_id', 'text', 'tokens', 'mwt'}.
    Each token is a dict with the CoNLL-U columns; FEATS is parsed into a dict."""
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
            if "-" in cols[0]:
                sent["mwt"].append((cols[0], cols[1]))
                continue
            if "." in cols[0]:
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


def read_all():
    """Read the three PerDT files; each sentence gets a 'file' key."""
    sentences = []
    for fn in FILES:
        for s in read_conllu(DATA_DIR / fn):
            s["file"] = fn
            sentences.append(s)
    return sentences
