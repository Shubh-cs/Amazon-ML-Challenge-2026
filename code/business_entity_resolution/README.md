# Business Entity Resolution — Amazon ML Challenge 2026

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

## 2. Directory Structure

```text
business_entity_resolution/
│
├── src/
│   └── experiments.ipynb
│
├── README.md
└── requirements.txt
```

The notebook contains the implementation of the preprocessing, blocking, candidate generation, and output-generation pipeline.

---

## 3. Requirements

The pipeline requires Python and the packages listed in `requirements.txt`.

Install the dependencies with:

```bash
pip install -r requirements.txt
```

The required packages are:

- pandas
- numpy
- rapidfuzz
- scikit-learn

---

## 4. Input Data

The challenge provides three independent data sources.

### Training data

```text
dataset/train/
├── train_source1.tsv
├── train_source2.tsv
├── train_source3.tsv
└── train_ground_truth.tsv
```

### Test data

```text
dataset/test/
├── test_source1.tsv
├── test_source2.tsv
└── test_source3.tsv
```

The test set contains Source 1 entities for which matching records must be identified in Source 2 and Source 3.

The final pipeline must generate predictions for every Source 1 test entity.

---

## 5. Data Loading

All challenge datasets are tab-separated files.

They are loaded using an explicit tab separator:

```python
pd.read_csv(path, sep="\t")
```

The pipeline uses the following fields:

- `entity_id`
- `business_name`
- `business_address`
- `country`

The source of an entity is indicated by its entity ID prefix:

- `S1-` — Source 1
- `S2-` — Source 2
- `S3-` — Source 3

---

## 6. Name Normalization

Business names contain variations such as punctuation differences, legal suffixes, abbreviations, and formatting differences.

The pipeline normalizes business names by:

1. Converting text to lowercase
2. Replacing punctuation and symbols with spaces
3. Splitting the name into tokens
4. Removing selected legal/business and title stopwords
5. Rejoining the remaining tokens

The normalization removes terms such as:

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
```

as well as selected titles such as:

```text
dr
mr
mrs
ms
smt
sri
shri
prof
```

The normalized representation is then used to construct the blocking key.

---

## 7. Address Number Extraction

Addresses can contain many variations in formatting. A lightweight structural feature used by the final blocking strategy is the first numeric address component.

The pipeline extracts the first value matching:

```text
\d+[A-Za-z]?
```

from the address.

For example, an address containing a leading number such as `123A` produces:

```text
123A
```

If no address number is found, the extracted value is empty.

---

## 8. Candidate Generation and Blocking

Comparing every Source 1 record with every Source 2 and Source 3 record would create an unnecessarily large comparison space.

The final pipeline therefore uses a deterministic blocking key called **K4**.

The K4 key is constructed from:

```text
country + normalized business name + address number
```

with the components combined into a single lookup key.

This blocking strategy was selected after evaluating several candidate-generation approaches on the training data. The final strategy prioritizes a substantially smaller candidate set while retaining useful matching coverage.

### K4 blocking

For each Source 1 entity, the pipeline constructs its K4 key and looks up records in Source 2 and Source 3 having the same K4 key.

Candidate retrieval is performed independently for Source 2 and Source 3.

---

## 9. Flat Index

A flat index is used to make exact K4 lookups efficient and memory-conscious.

For each indexed dataset, the implementation stores:

- sorted unique blocking keys
- an index-pointer array
- entity IDs corresponding to the indexed records

The lookup operation uses `numpy.searchsorted` to locate a blocking key without constructing large Python dictionaries of lists.

This allows candidate retrieval using the K4 blocking key while keeping the representation compact.

---

## 10. Candidate Bucket Handling

Some blocking keys can correspond to a large number of records.

To prevent extremely large candidate buckets from producing excessive candidate pairs, the lookup function applies a maximum bucket size of:

```text
2000
```

If a blocking bucket exceeds this limit, that bucket is not expanded into the candidate list.

For normal-sized buckets, all entity IDs belonging to the matching K4 key are returned as candidates.

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

This file represents the candidate set used by the final matching stage.

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

## 13. Output Files

The final submission package contains:

```text
output/
├── matching_results.tsv
└── candidate_pairs.tsv
```

### `matching_results.tsv`

Contains the final predicted matches for every Source 1 test entity.

### `candidate_pairs.tsv`

Contains the candidate Source 2 and Source 3 entity IDs generated by the final blocking stage for every Source 1 test entity.

Every final matched ID is therefore also present in the corresponding candidate list.

---

## 14. Final Test Run

The final pipeline was run on the complete test set.

The test set contained:

```text
1,732,544 Source 1 entities
```

The final candidate-generation run produced:

```text
Total candidate pairs: 2,302,572
Average candidates per entity: 1.329
Runtime: 116.75 seconds
```

The final output files were:

```text
output/matching_results.tsv
output/candidate_pairs.tsv
```

---

## 15. Validation

Before submission, the generated output files were checked using the challenge-provided validation utility.

The validation checks the required output structure and verifies that:

- Every Source 1 test entity is present.
- There is exactly one row per Source 1 entity.
- Matching IDs use Source 2 or Source 3 prefixes.
- There are no duplicate IDs within an ID list.
- Candidate and matching outputs are structurally consistent.

The additional test-set ID check was also performed to verify that the submitted Source 2 and Source 3 IDs exist in the test data.

The final generated files passed validation, including the test-set ID existence check.

---

## 16. Reproducibility

To reproduce the pipeline:

1. Install the dependencies from `requirements.txt`.
2. Place the challenge dataset in the expected `dataset/` structure.
3. Open:

```text
src/experiments.ipynb
```

4. Set the dataset/output paths to the local environment.
5. Run the notebook cells in order.
6. The final pipeline builds the test Source 2 and Source 3 K4 indexes.
7. It generates candidate pairs for every Source 1 test entity.
8. It writes:

```text
output/matching_results.tsv
output/candidate_pairs.tsv
```

The notebook contains the complete implementation of the final pipeline.

---

## 17. Notes

The final solution uses only the provided challenge data.

No external business databases, business lookup APIs, geocoding services, or external entity-resolution services are used.

The final approach is deterministic and does not require downloading or serving an external machine-learning model.