# Amazon ML Challenge 2026 — Business Entity Resolution

A business entity resolution system developed for the **Amazon ML Challenge 2026**.

The challenge involved identifying records referring to the same real-world business across three independent data sources, despite differences in names, addresses, formatting, abbreviations, transliteration, typos, and other forms of noise.

The competition phase is complete. This repository contains the development work, experiments, validation, and final competition approach. It also serves as the starting point for continued experimentation with entity-resolution methods after the competition.

---

## Competition

**Amazon ML Challenge 2026**  
**Problem:** Business Entity Resolution

### Team

**Team Name:** Gradient Descent

**Team Members:**

- Shubhneet Kaur
- Gurkirat Singh

### Competition Result

Final submitted leaderboard score:

**0.517**

The final competition submission used a deterministic blocking-based entity resolution pipeline.

---

## 1. Overview

This project implements a business entity resolution pipeline for the Amazon ML Challenge 2026.

The task is to identify records in **Source 2** and **Source 3** that correspond to each entity in **Source 1**, despite variations and noise in business names and addresses.

The final pipeline uses:

1. Name normalization
2. Address-number extraction
3. Deterministic blocking using a composite key
4. A memory-efficient flat index for candidate retrieval
5. Candidate generation from the test Source 2 and Source 3 datasets
6. Final output generation for both matching results and candidate pairs

The pipeline uses only the provided challenge data and does not use external business lookup services or external data augmentation.

---

## 2. Problem Statement

The dataset contains three independent sources of business records:

- Source 1
- Source 2
- Source 3

The task is to determine which Source 2 and Source 3 records refer to the same real-world business as each Source 1 record.

The sources do not share a common entity ID.

The data contains several types of variation and noise, including:

- punctuation differences
- legal suffix differences
- abbreviations
- word-order changes
- spelling errors
- transliteration differences
- missing address components
- different address formatting
- non-Latin names
- trade or DBA names

The competition metric was macro-averaged **F₀.₅**, which places greater emphasis on precision than recall.

This makes candidate generation particularly important: incorrect candidates can reduce precision, while an overly restrictive blocking strategy can remove true matches before the matching stage.

---

## 3. Input Data

The challenge provides three independent data sources.

### Training Data

```text
dataset/train/
├── train_source1.tsv
├── train_source2.tsv
├── train_source3.tsv
└── train_ground_truth.tsv
```

The training data contains labelled Source 1 entities and their corresponding Source 2 and Source 3 matches.

### Test Data

```text
dataset/test/
├── test_source1.tsv
├── test_source2.tsv
└── test_source3.tsv
```

The test set contains Source 1 entities for which matching records must be identified in Source 2 and Source 3.

The ground-truth labels for the competition test set are hidden and are not included in this repository.

### Data Fields

The pipeline uses the following fields:

- `entity_id`
- `business_name`
- `business_address`
- `country`

The source of an entity is indicated by its entity ID prefix:

- `S1-` — Source 1
- `S2-` — Source 2
- `S3-` — Source 3

All challenge datasets are tab-separated files.

They are loaded using:

```python
pd.read_csv(path, sep="\t")
```

---

## 4. Dataset Split and Validation

Because the competition test-set ground truth is hidden, development and evaluation were performed using the labelled training data.

The training Source 1 entities were split into:

- **80% training/development set**
- **20% validation set**

The split used:

```python
random_state=42
```

This allowed the same validation set to be reproduced across experiments.

Source 2 and Source 3 were not split at this stage because they serve as candidate databases against which Source 1 entities are matched.

The validation framework uses the competition's macro-averaged **F₀.₅** metric.

For each Source 1 entity, predicted and ground-truth match IDs are converted into sets and compared.

The metric gives special treatment to entities with no true matches:

- no true matches + no predictions → score `1`
- no true matches + one or more predictions → score `0`

This reflects the precision-sensitive nature of the competition.

---

## 5. Name Normalization

Business names contain variations such as punctuation differences, legal suffixes, abbreviations, formatting differences, and differences in character representation.

The final normalization function performs the following operations:

1. Converts the business name to lowercase.
2. Uses Unicode character categories to replace punctuation and symbols with spaces.
3. Splits the resulting string into tokens.
4. Removes selected legal/company suffixes and common titles.
5. Rejoins the remaining tokens into a normalized string.

The final stopword set included:

```text
inc
incorporated
ltd
limited
pvt
private
corp
corporation
llc
llp
co
company
dr
mr
mrs
ms
smt
sri
shri
prof
m
s
the
```

The normalized representation is then used to construct the blocking key.

### Unicode Normalization

An earlier normalization experiment used a regular expression based on `\w`.

Testing showed that this approach could corrupt non-Latin text such as Devanagari business names.

For example, Hindi text could be separated into individual characters because combining marks were not preserved correctly.

The final normalization therefore uses Unicode character categories instead of relying on the earlier regular-expression approach.

This preserves letters and combining marks across scripts while still replacing punctuation and symbols.

---

## 6. Address Number Extraction

Addresses can contain many variations in formatting.

A lightweight structural feature used by the final blocking strategy is the first numeric address component.

The pipeline extracts the first value matching:

```text
\b\d+[A-Za-z]?\b
```

from the address.

For example, an address containing:

```text
123A Main Street
```

produces:

```text
123A
```

If no address number is found, the extracted value is an empty string.

The extracted address number is incorporated into the final composite blocking key.

---

## 7. Candidate Generation and Blocking

Comparing every Source 1 record with every Source 2 and Source 3 record would create an unnecessarily large comparison space.

Candidate generation was therefore treated as a critical part of the solution.

A number of candidate-generation approaches were investigated during development, including:

- exact normalized-name matching
- country + first two name tokens
- country + address number
- country + normalized name + address number
- rare-token blocking
- prefix-based blocking
- Jaccard-based candidate filtering
- character trigram candidate generation
- token inverted-index approaches
- broader V3 blocking

The experiments demonstrated a trade-off between:

- candidate recall
- candidate volume
- precision
- computational cost
- memory usage

The broader V3 blocking strategy achieved approximately **0.79265 candidate recall**, but produced a very large candidate pool.

Subsequent attempts to apply pairwise similarity computations to large candidate sets resulted in excessive runtime and memory usage.

The final strategy therefore used a much more selective composite key.

---

## 8. Final K4 Blocking Strategy

The final blocking key was:

```text
country || normalized_business_name || address_number
```

The same key construction was applied independently to Source 2 and Source 3.

For example:

```text
US||normalized business name||123
```

For each Source 1 entity, the pipeline constructs its K4 key and looks up records in Source 2 and Source 3 having the same K4 key.

Candidate retrieval is performed independently for Source 2 and Source 3.

### Why K4?

The final K4 strategy was selected because it provided a very small candidate space and was computationally practical at the full test-set scale.

It trades some candidate recall for substantially lower candidate volume.

This was particularly important because broader blocking approaches generated millions of candidate comparisons and made subsequent pairwise similarity calculations impractical.

---

## 9. Flat Index

A flat index is used to make exact K4 lookups efficient and memory-conscious.

For each indexed dataset, the implementation stores:

- sorted unique blocking keys
- an index-pointer array
- entity IDs corresponding to the indexed records

The lookup operation uses:

```python
numpy.searchsorted
```

to locate a blocking key.

This avoids repeatedly scanning the complete Source 2 or Source 3 dataset for every Source 1 entity.

The same indexing strategy is used independently for Source 2 and Source 3.

---

## 10. Candidate Bucket Handling

Some blocking keys can correspond to a large number of records.

To prevent extremely large candidate buckets from producing excessive candidate pairs, the lookup function applies a maximum bucket size of:

```text
2000
```

If a blocking bucket exceeds this limit, that bucket is not expanded into the candidate list.

For normal-sized buckets, all entity IDs belonging to the matching K4 key are returned as candidates.

This prevents common or pathological keys from creating disproportionately large candidate sets.

---

## 11. Final Candidate Set

The final candidate set is generated directly from the **test Source 2 and Source 3 indexes**.

For each Source 1 test entity:

1. Construct its normalized K4 key.
2. Look up the key in the test Source 2 index.
3. Look up the key in the test Source 3 index.
4. Combine the returned Source 2 and Source 3 entity IDs.
5. Store the resulting IDs as the candidate list.

The resulting candidate set is written to:

```text
output/candidate_pairs.tsv
```

This file represents the final candidate set used by the production pipeline rather than an earlier intermediate blocking stage.

---

## 12. Final Matching Output

The final matching output is generated from the candidate set produced by the K4 blocking stage.

The resulting matches are written to:

```text
output/matching_results.tsv
```

The output contains:

```text
source1_entity_id
matched_entity_ids
```

where `matched_entity_ids` contains comma-separated Source 2 and Source 3 entity IDs.

If no candidates are produced for a Source 1 entity, the matched ID field is left empty.

---

## 13. Matching Model

The final submitted approach was a **deterministic rule-based matcher**, rather than a trained machine-learning classifier.

A Source 2 or Source 3 record was retained as a match when it shared the final composite blocking key with the Source 1 record:

```text
country || normalized_business_name || address_number
```

The resulting records were used directly to construct the final matching output.

No classifier probability threshold was used in the final pipeline.

Several similarity-based methods were explored during development, including:

- RapidFuzz token similarity
- Jaccard similarity
- token-based candidate filtering
- character trigram methods

These approaches were not used in the final full-scale pipeline because of their computational cost or insufficient candidate recall.

---

## 14. Experiments

A large number of candidate-generation and matching approaches were investigated before selecting the final solution.

### Blocking Experiments

| Experiment | Result | Decision |
|---|---:|---|
| V1 blocking | 0.75636 candidate recall | Improved further |
| V2 blocking | 0.78433 candidate recall | Improved further |
| V3 blocking | 0.79265 candidate recall | High recall but very large candidate pool |
| V4 address-augmented blocking | 0.25588 candidate recall | Rejected |
| Jaccard prefilter | Up to 0.7344 candidate recall | Rejected |
| Token inverted index | Up to 0.7279 recall after backfill | Rejected |
| Character trigram blocking | 0.7889 candidate recall | Rejected due to runtime |
| Compact-prefix blocking | Up to 0.7819 candidate recall | Rejected due to candidate volume/runtime |
| K2 + K4 + rare-token blocking | Up to 0.7641 candidate recall | Rejected |
| Final K4 blocking | 0.306779 candidate recall | Selected |

### Similarity Experiment

A RapidFuzz experiment using the broader V3 candidate set was run on approximately 20,000 Source 1 entities.

The computation took approximately:

```text
51.2 minutes
```

and resulted in extremely high memory usage, reaching approximately:

```text
98–99% RAM utilization
```

before the kernel restarted.

This demonstrated that applying large-scale pairwise fuzzy similarity to the broader candidate pool was not practical in the available environment.

The experiment was therefore not used for the final full-scale pipeline.

---

## 15. Earlier Exact-Matching Submission

An earlier experiment used exact normalized-name matching.

The production run generated:

- **1,732,544 Source 1 entities**
- **42,651,215 predicted IDs before capping**

A maximum of 10 predictions per Source 1 entity was subsequently applied to make the output manageable.

That submission passed the official validator and achieved a leaderboard score of:

**0.416**

This result demonstrated that exact normalized-name matching alone produced too many ambiguous matches and motivated the move toward more selective multi-attribute blocking.

---

## 16. Validation Results

The final K4 configuration was evaluated on a labelled validation sample.

The reported final K4 validation results were:

| Metric | Value |
|---|---:|
| Validation entities | 2,820 |
| Average candidate pool | 1.424 |
| Candidate recall | 0.306779 |
| Candidate precision | 0.797809 |
| Macro F₀.₅ | 0.486437 |

An earlier experimental configuration achieved:

| Metric | Value |
|---|---:|
| Macro F₀.₅ | 0.5769 |
| Precision | 0.6989 |
| Recall | 0.4031 |

That higher-scoring configuration combined exact candidate generation with name/address similarity on a validation sample.

It was not selected for final production because the associated similarity-based processing was not practical at the full test-set scale.

These validation results therefore represent different experimental configurations and should not be interpreted as a direct head-to-head comparison of identical pipelines.

---

## 17. Final Production Run

The final production pipeline was run on the complete competition test set.

The test set contained:

```text
1,732,544 Source 1 entities
```

The final production run produced:

```text
Total candidate pairs: 2,302,572
Average candidates per entity: 1.329
Runtime: 116.75 seconds
Runtime: approximately 1.95 minutes
```

### Test Source 2 K4 Index

The final test Source 2 index contained:

```text
Unique keys: 4,411,170
Entity IDs indexed: 4,887,273
```

### Test Source 3 K4 Index

The final test Source 3 index contained:

```text
Unique keys: 4,618,594
Entity IDs indexed: 5,082,316
```

Total test-index construction time was:

```text
633.46 seconds
approximately 10.6 minutes
```

The final output files were:

```text
output/matching_results.tsv
output/candidate_pairs.tsv
```

---

## 18. Submission Validation

Before submission, the generated output files were checked using the challenge-provided validation utility.

The validation confirmed:

- every required Source 1 test entity was present
- there was exactly one row per Source 1 entity
- matching IDs used Source 2 or Source 3 prefixes
- there were no structural blocking issues
- candidate and matching outputs were structurally consistent

An additional test-set ID check was also performed to verify that the submitted Source 2 and Source 3 IDs actually existed in the test datasets.

The final validation reported:

```text
required S1 entities: 1732544
valid S2/S3 match IDs: 9969589
matching_results.tsv: 1732544 rows
candidate_pairs.tsv: 1732544 rows

PASS — no blocking issues found. Safe to submit.
```

The final generated files therefore passed the official validator, including the test-set ID existence check.

---

## 19. Error Analysis

### False Positives

False positives in the final blocking strategy can occur when different businesses share the same:

- country
- normalized business name
- address number

This is particularly possible for common business names or businesses with similar naming patterns.

Because the final production method does not apply a second trained classifier or fuzzy-similarity threshold after the K4 lookup, such records can remain in the final matching output.

### False Negatives

The main source of false negatives is the strict nature of the final composite key.

A true match can be missed when:

- the business name contains a typo
- the name is transliterated differently
- the business name uses another writing system
- the business uses a substantially different trade or DBA name
- the address number is missing
- the address number is represented differently
- the normalized names do not become identical

During the experiments, difficult cases included:

- typo variations
- accented or Unicode variants
- concatenated business names
- transliteration differences
- non-Latin names
- substantial business-name changes

These observations motivated experiments with fuzzy matching, Jaccard similarity, token indexes, character trigrams, and prefix-based blocking.

However, these approaches either reduced recall too much or introduced substantial computational cost at the full dataset scale.

---

## 20. Repository Structure

The public development repository is organized as follows:

```text
Amazon-ML-Challenge-2026/
│
├── code/
│   └── business_entity_resolution/
│       ├── src/
│       │   └── experiments.ipynb
│       ├── README.md
│       └── requirements.txt
│
├── EXPERIMENT_LOG.md
├── README.md
├── extract_data.py
└── .gitignore
```

The main development notebook is:

```text
code/business_entity_resolution/src/experiments.ipynb
```

It contains the development experiments, validation work, candidate-generation implementations, and final production pipeline.

The original competition dataset and large generated submission files are intentionally not stored in the public development repository.

---

## 21. Requirements

The final submission environment used the following pinned dependencies:

```text
pandas==2.3.3
numpy==2.4.1
rapidfuzz==3.14.6
scikit-learn==1.9.1
```

Install the dependencies with:

```bash
pip install -r code/business_entity_resolution/requirements.txt
```

---

## 22. Reproducing the Work

To reproduce the development and final pipeline:

1. Install the dependencies from `requirements.txt`.
2. Obtain the challenge dataset separately.
3. Place the dataset in the expected local dataset structure.
4. Open:

```text
code/business_entity_resolution/src/experiments.ipynb
```

5. Set the dataset and output paths for the local environment.
6. Run the notebook cells in order.
7. The notebook performs preprocessing and normalization.
8. The notebook contains the candidate-generation experiments.
9. The final section builds the test Source 2 and Source 3 K4 indexes.
10. The final production pipeline generates candidate pairs and matching results.

The final output files are:

```text
output/matching_results.tsv
output/candidate_pairs.tsv
```

The competition dataset is not included in this repository.

---

## 23. Experiment Log

The development process involved many experiments and implementation decisions.

The experiment history is documented separately in:

```text
EXPERIMENT_LOG.md
```

The log records:

- experiment number
- date
- approach or change
- measured result
- decision taken

The experiment log is intended to preserve the reasoning behind the progression from broad candidate generation to the final selective K4 strategy.

---

## 24. Post-Competition Development

The competition solution is now being treated as a baseline for continued work on business entity resolution.

The hidden competition test-set ground truth is not available, so future experiments will be evaluated using the labelled training data and controlled validation splits.

Potential future directions include:

- improved multilingual normalization
- transliteration handling
- typo-tolerant candidate generation
- character n-gram methods
- TF-IDF representations
- fuzzy matching
- learned pairwise classifiers
- hard-negative mining
- address similarity
- country-specific normalization
- ensemble blocking
- precision/recall optimization
- scalable inference
- learned entity representations
- hybrid deterministic and machine-learning approaches

The goal is to evolve the competition baseline into a more robust and scalable entity-resolution system.

---

## 25. Competition Test Set

The competition test set contains Source 1, Source 2, and Source 3 records but does not contain publicly available ground-truth labels.

Therefore, predictions made on the competition test set cannot be independently scored after the competition.

The hidden labels used by the competition leaderboard are not included in this repository.

Future development will use the labelled training data and controlled validation splits for measurable experimentation.

---

## 26. Competition Submission

The final competition submission used:

```text
matching_results.tsv
candidate_pairs.tsv
```

The generated files passed the official validation utility, including the test-set ID existence check.

The final submitted leaderboard score was:

**0.517**

The competition submission artifacts are intentionally kept separate from the public development repository because of their size.

---

## 27. Status

**Competition phase: Complete**

**Current phase: Post-competition experimentation**

The competition provided a practical baseline for studying the trade-offs between:

- candidate recall
- precision
- candidate volume
- runtime
- memory usage
- deterministic matching
- scalable inference

The next phase of the project will focus on improving the robustness of the entity-resolution pipeline while retaining measurable evaluation through labelled validation data.
