#Experiment & Submission Log

This file records the experiments and competition submissions made by Team Gradient Descent.
| Submission | Date | Approach/Change | Score | Decision |
| -- | -- | -- | -- | -- |
| 1 | 2026-09-27 | V3 blocking + exact normalized-name matching; max 10 predictions per S1 | 0.416 | Reject; exact-name matching has too much ambiguity. Move to selective multi-attribute blocking + pairwise scoring. |
| 2 | 2026-09-27 | K4-only production attempt using `country + normalized_name + address_number` | N/A | Do not retain as final submission. A production indexing bug was discovered: the initial production lookup referenced training-built K4 indexes instead of test Source 2/Source 3 indexes. The output was regenerated correctly for Submission #3. |
| 3 | 2026-09-27 | Corrected K4-only production using dedicated TEST Source 2/Source 3 indexes; maximum bucket size 2000 | 0.517 leaderboard | Final submitted solution. Passed the official validator, including `--check-ids`. |

## Final Approach

The final production pipeline uses deterministic K4 blocking:

`country + normalized business name + address number`

Separate flat indexes are built for test Source 2 and test Source 3. Candidate IDs are retrieved using `numpy.searchsorted`. Buckets larger than 2000 records are not expanded.

Final production statistics:

- Source 1 entities: 1,732,544
- Candidate pairs: 2,302,572
- Average candidates per entity: 1.329
- Test index construction time: 633.46 seconds
- Production candidate-generation time: 116.75 seconds
- Final validation: PASS, including test-set ID existence check

## Rejected Experiments

The following approaches were evaluated during development and rejected because of insufficient recall, excessive candidate volume, or computational cost:

- V1/V2/V3/V4 blocking variants
- Jaccard prefiltering
- Token inverted indexes
- Character trigram blocking
- Compact-prefix blocking
- Rare-token blocking combinations
- Large-scale RapidFuzz pairwise scoring
- Exact-name matching as the final strategy

The broader V3 candidate set had substantially higher candidate recall but was too large for practical full-scale fuzzy pairwise scoring on the available hardware.