# Comparable Corpora in Cross-Linguistic Research: Nominal Number in English, Czech, and Greek

Repository for the paper submitted to the **19th Workshop on Building and Using Comparable Corpora (BUCC)**, hosted at **LREC 2026**.

---

## Contributors

**Konstantinos Diamantopoulos**  
PhD Student, Institute of Formal and Applied Linguistics  
Faculty of Mathematics and Physics, Charles University, Prague  
diamantopoulos@ufal.mff.cuni.cz

**Magda Ševčíková**  
Associate Professor, Institute of Formal and Applied Linguistics  
Faculty of Mathematics and Physics, Charles University, Prague  
sevcikova@ufal.mff.cuni.cz

---

## Description

This paper examines the use of comparable corpora for contrastive research on the category of nominal number across three languages — English, Czech, and Greek. Two objectives are pursued: a cross-linguistic analysis of number and an assessment of the impact of automatic annotation on linguistic findings. Corpora of comparable size and composition were compiled from the Leipzig Corpora Collection and automatically annotated using two open-access tools, Stanza and UDPipe, producing six datasets each containing approximately 5 million sentences and 100 million tokens.

---

## Repository Contents

| File | Description |
|------|-------------|
| `preprocessing_and_annotation.py` | Two-stage pipeline: text cleaning + UDPipe API annotation + Stanza annotation |
| `calculate_noun_tokens_number_features.py` | Stage 0: counts noun tokens and Number feature distribution across CoNLL-U files |
| `calculate_lemma_distributions.py` | Stage 1: computes plural ratios per noun lemma and generates LaTeX distribution table |
| `calculation_candidate_validation_statistics.py` | Stage 2: validates grammar-derived singularia/pluralia tantum candidates against corpus |
| `generate_distribution_plots.py` | Stage 3: generates distribution plots with candidate dots overlaid |
| `candidates.json` | Grammar-derived singularia and pluralia tantum candidate lists for all three languages |
| `english_annotations.csv` | Manual annotation quality evaluation — English (500 tokens per tool - 1000 in total) |
| `czech_annotations.csv` | Manual annotation quality evaluation — Czech (500 tokens per tool - 1000 in total) |
| `greek_annotations.csv` | Manual annotation quality evaluation — Greek (500 tokens per tool - 1000 in total) |

---

## Data

The six annotated datasets (two per language) are available in the LINDAT/CLARIAH-CZ repository:  
**http://hdl.handle.net/11234/1-6120**

### Corpus Sources

Corpora were compiled from the [Leipzig Corpora Collection](https://wortschatz.uni-leipzig.de/en/download), combining news and Wikipedia texts in a 4:1 ratio (80% news, 20% Wikipedia), with news components spanning 2019–2024 and Wikipedia snapshots from 2016–2021.

### Annotation Tools

| Tool | Version | Models |
|------|---------|--------|
| [Stanza](https://stanfordnlp.github.io/stanza/) | 1.11.0 | UD 2.15 (`en`, `cs`, `el`) |
| [UDPipe 2](https://ufal.mff.cuni.cz/udpipe/2) | latest | UD 2.17 (`english-gum`, `czech-pdtc`, `greek-gud`) |

---

## Pipeline

```
Raw corpora (Leipzig)
        │
        ▼
Stage 0: preprocessing_and_annotation.py
         (text cleaning + Stanza + UDPipe annotation → CoNLL-U files)
        │
        ▼
Stage 1: calculate_noun_tokens_number_features.py
         (noun token counts and Number feature distribution)
        │
        ▼
Stage 2: calculate_lemma_distributions.py
         (plural ratio per lemma → LaTeX distribution table)
        │
        ▼
Stage 3: calculation_candidate_validation_statistics.py
         (grammar-derived candidate validation → LaTeX validation table)
        │
        ▼
Stage 4: generate_distribution_plots.py
         (distribution plots with singularia/pluralia tantum candidates overlaid)
```

---

## Candidate Lists

Grammar-derived candidate counts per language:

| Language | Singularia tantum | Pluralia tantum |
|----------|-------------------|-----------------|
| English  | 54                | 87              |
| Czech    | 27                | 54              |
| Greek    | 22                | 59              |

---

## Requirements

```bash
pip install stanza
pip install scipy matplotlib numpy
```

---

## Acknowledgements

This research was supported by the Czech Science Foundation (Project No. GA26-21822S) and used data and tools provided by the LINDAT/CLARIAH-CZ Research Infrastructure (Ministry of Education, Youth and Sports of the Czech Republic, Project No. LM2023062).
