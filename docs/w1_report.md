# W1 hard gate report

Multi-source synthetic data + retrieval baseline + reference benchmark subsets. Per design Section 8 W1 gate criteria.

## 1. Multi-source generator

Generated under `data/synthetic/`, seed=42, days=7.

| Source | Count |
|---|---:|
| calendar_events | 178 |
| email_emails | 1501 |
| gdocs_docs | 50 |
| github_prs | 100 |
| github_repos | 30 |
| jira_tickets | 200 |
| slack_channels | 50 |
| slack_dms | 63 |
| slack_messages | 1642 |

Determinism (same seed -> byte-equal files across 6 sources): **PASS**

## 2. Entity overlap matrix (30 users by 6 sources)

| User | Slack | Jira | Calendar | GitHub | GDocs | Email |
|---|---:|---:|---:|---:|---:|---:|
| Marco van der Berg | 131 | 26 | 22 | 31 | 8 | 143 |
| Sarah Chen | 150 | 30 | 21 | 15 | 14 | 138 |
| Hiroshi Tanaka | 134 | 22 | 22 | 15 | 6 | 130 |
| Anna Muller | 151 | 29 | 24 | 17 | 8 | 160 |
| Alice Rodriguez | 110 | 17 | 22 | 29 | 8 | 132 |
| Tom Nguyen | 121 | 19 | 23 | 23 | 9 | 151 |
| Liam OBrien | 92 | 18 | 21 | 30 | 12 | 163 |
| Priya Patel | 111 | 23 | 17 | 18 | 6 | 150 |
| Diego Fernandez | 112 | 24 | 19 | 29 | 10 | 123 |
| Maya Goldberg | 113 | 23 | 20 | 14 | 12 | 145 |
| Ahmed Hassan | 100 | 17 | 28 | 20 | 11 | 147 |
| Yuki Sato | 99 | 21 | 16 | 17 | 12 | 136 |
| Emma Bakker | 188 | 3 | 23 | 1 | 10 | 150 |
| Lukas Schmidt | 143 | 8 | 19 | 3 | 10 | 153 |
| Sophie Dupont | 127 | 6 | 23 | 4 | 10 | 158 |
| Rajesh Kumar | 142 | 6 | 20 | 1 | 16 | 145 |
| Mei Lin | 124 | 3 | 21 | 3 | 8 | 136 |
| Olivia Janssen | 134 | 10 | 17 | 3 | 9 | 142 |
| Noah de Vries | 110 | 6 | 17 | 1 | 12 | 144 |
| Karim Bensaid | 197 | 7 | 21 | 4 | 7 | 137 |
| Helena Stojanovic | 130 | 10 | 18 | 3 | 10 | 151 |
| Daniel Weber | 110 | 4 | 17 | 4 | 8 | 139 |
| Lisa Park | 94 | 2 | 20 | 5 | 11 | 153 |
| James OConnor | 78 | 9 | 16 | 3 | 12 | 156 |
| Sven Olsen | 137 | 8 | 18 | 3 | 13 | 155 |
| Isabella Romano | 91 | 10 | 18 | 3 | 6 | 143 |
| Sofia Almeida | 112 | 9 | 21 | 2 | 10 | 150 |
| Jane van Dijk | 70 | 3 | 13 | 5 | 9 | 148 |
| Mateusz Kowalski | 107 | 7 | 22 | 2 | 9 | 150 |
| Aiyana Singh | 94 | 11 | 20 | 3 | 10 | 147 |

Full 30 / 30 / 30 / 30 / 30 / 30 overlap: **PASS**

## 3. Nine cross-source injection patterns

- **[PASS]** 1. Sarah Thursday conflict (Alice 1:1 vs all-hands)
- **[PASS]** 2. >=5 Jira tickets cite a GDoc id (count=5)
- **[PASS]** 3. >=3 Slack messages reference a calendar event_id (count=3)
- **[PASS]** 4. >=1 q3-launch PR blocking Sarah's review
- **[PASS]** 5. #leadership excludes Sarah, 3-5 members (members=['daniel.weber', 'emma.bakker', 'marco.vandenberg', 'olivia.janssen', 'sofia.almeida'])
- **[PASS]** 6. >=3 HR-private GDocs (acl=['hr']) (count=4)
- **[PASS]** 7. >=3 VP-Eng DMs to Sarah (count=3)
- **[PASS]** 8. Monday production incident thread w/ replies
- **[PASS]** 9. EY contract follow-up email stale + high priority

## 4. Reference baselines (retrieval component sanity check, W4)

- HotpotQA distractor subset (n=100, seed=42): **PASS**
  - cache: `data/reference_baselines/hotpotqa/subset_n100_seed42.json` (597,993 bytes, 100 items)
- MS Marco passage subset (n=50, seed=42): **PASS**
  - cache: `data/reference_baselines/ms_marco/subset_n50_seed42.json` (212,347 bytes, 50 items)

## 5. Baseline RAG over GDocs corpus

- Qdrant collection `gdocs` indexed: **PASS** (count=50)

Top-5 for demo query: `Today's priorities for Sarah Chen`

| Rank | Score | Title |
|---:|---:|---|
| 1 | 0.446 | User-centric coherent Internet solution (31) |
| 2 | 0.430 | Streamlined disintermediate capacity (30) |
| 3 | 0.422 | Quarterly Business Review |
| 4 | 0.414 | Q3 Roadmap Plan |
| 5 | 0.407 | Streamlined value-added Local Area Network (38) |

## Summary

- **[PASS]** Generator
- **[PASS]** Overlap matrix
- **[PASS]** Injections
- **[PASS]** Reference baselines
- **[PASS]** Baseline RAG

### W1 hard gate: **PASS**

