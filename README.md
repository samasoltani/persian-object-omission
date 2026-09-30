# What Makes an Object Omissible? Complex Predicates and Object Omission in Persian

Code and analysis for a corpus-based computational study of indefinite (free) object omission in Persian.
The study tests the discourse-pragmatic factors proposed by Salimi & Rezai (2024/1403) and asks whether
complex predicates (non-verbal element + light verb) predict object omission.

> Status: work in progress. Results are not final.

## Research questions

1. Are transitive complex predicates used without an overt object more often than transitive simple verbs?
2. Among complex predicates, does the type of light verb (kardan, zadan, dadan, gereftan, ...) matter?
3. Is the effect explained by object predictability (prototypical complement / selectional preference strength)?
4. Do Salimi & Rezai's factors (genericity, indefiniteness, aspect, structural omission, ...) still predict omission once verb type is controlled?

## Data

The corpus is **not** included in this repository. Download the Persian Dependency Treebank (Universal Dependencies version):

```
git clone https://github.com/UniversalDependencies/UD_Persian-PerDT.git
```

Copy the three `.conllu` files into `data/perdt/`.

- Rasooli, M. S., Kouhestani, M., & Moloodi, A. (2013). Development of a Persian syntactic dependency treebank. NAACL-HLT 2013.
- Rasooli, M. S., Safari, P., Moloodi, A., & Nourian, A. (2022). The Persian Dependency Treebank made universal. LREC 2022.

## Project structure

```
data/perdt/        corpus files (not tracked)
data/valency/      verb valency lexicon (not tracked)
outputs/tables/    result tables
outputs/figures/   figures
annotation/        manual annotation sample
01-..., 02-...     analysis scripts, run in numeric order
```

## How to run

Run the scripts in numeric order from the project root (e.g. in PyCharm, with `hazf_mafoul` opened as the project).

## Requirements

Python 3.10+, `conllu`, `pandas`, `numpy`, `scipy`, `statsmodels` (a `requirements.txt` will be added).

## Citation

To be added after publication.
