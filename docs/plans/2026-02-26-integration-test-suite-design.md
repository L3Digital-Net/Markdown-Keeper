# Integration Test Suite: Semantic Search Quality

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an integration test suite that validates MarkdownKeeper's semantic search quality against the KPIs defined in the Project Design Document. Tests run exclusively inside the devcontainer where sentence-transformers and faiss-cpu are available.

**Environment:** Devcontainer only (Python 3.12, sentence-transformers, faiss-cpu)

---

## Context

MarkdownKeeper's 174 unit tests all run with the hash-based embedding fallback (64-dim pseudo-embeddings). The ML-powered search path (sentence-transformers all-MiniLM-L6-v2, 384-dim real vectors) has never been validated in an automated way. The Project Design Document defines concrete KPIs for v1.0.0 readiness:

- precision@5 >= 90%
- Semantic search latency p95 < 150ms
- Embedding generation throughput ~500 docs/min

This suite validates those KPIs against a curated test corpus.

---

## Architecture

```
tests/integration/
├── __init__.py
├── test_semantic_quality.py       # 7 test methods (unittest.TestCase)
├── semantic_cases.json            # ~15 query cases with expected doc matches
└── fixtures/                      # 25 curated markdown files
    ├── kubernetes-setup.md
    ├── docker-basics.md
    ├── ...
    └── performance-benchmarking.md

scripts/
└── run-integration-tests.sh       # Dependency gate + test runner
```

Single test module with `setUpClass` creating a shared DB + embeddings. This avoids re-generating embeddings per test method (~3-5s for 25 docs).

---

## Test Corpus (25 fixture files)

Three categories to test cross-domain semantic distinction:

### Sysadmin (12 files)
| File | Key concepts |
|------|-------------|
| `kubernetes-setup.md` | kubernetes, cluster, kubectl, pods |
| `docker-basics.md` | docker, container, image, dockerfile |
| `nginx-ssl-config.md` | nginx, ssl, tls, certificate, reverse-proxy |
| `postgresql-backup.md` | postgresql, backup, pg_dump, restore |
| `dns-troubleshooting.md` | dns, nameserver, dig, nslookup |
| `prometheus-alerting.md` | prometheus, alerting, grafana, metrics |
| `ssh-key-management.md` | ssh, key, authentication, authorized_keys |
| `zfs-pool-management.md` | zfs, pool, snapshot, raid |
| `systemd-service-files.md` | systemd, service, unit, timer |
| `fail2ban-setup.md` | fail2ban, intrusion, ban, jail |
| `ansible-playbooks.md` | ansible, playbook, inventory, role |
| `traefik-routing.md` | traefik, routing, load-balancer, middleware |

### Development (8 files)
| File | Key concepts |
|------|-------------|
| `python-testing-patterns.md` | pytest, unittest, mock, fixtures |
| `git-branching-strategy.md` | git, branch, merge, rebase |
| `rest-api-design.md` | rest, api, http, endpoints, json |
| `typescript-generics.md` | typescript, generics, type, interface |
| `sql-query-optimization.md` | sql, query, index, explain, performance |
| `ci-pipeline-best-practices.md` | ci, pipeline, github-actions, automation |
| `code-review-checklist.md` | code-review, pull-request, quality |
| `debugging-memory-leaks.md` | memory, leak, profiling, heap |

### General/Mixed (5 files)
| File | Key concepts |
|------|-------------|
| `project-documentation-guide.md` | documentation, markdown, readme |
| `incident-response-playbook.md` | incident, response, escalation, postmortem |
| `onboarding-new-developers.md` | onboarding, setup, environment, getting-started |
| `architecture-decision-records.md` | adr, architecture, decision, trade-off |
| `performance-benchmarking.md` | benchmark, performance, latency, throughput |

Each file: 200-500 words, frontmatter with title/tags/category/concepts, 2-3 headings, realistic content.

---

## Semantic Query Cases (~15 queries)

`tests/integration/semantic_cases.json` format:
```json
[
  {
    "query": "how to set up kubernetes",
    "expected_titles": ["kubernetes-setup.md"],
    "type": "direct_match"
  },
  {
    "query": "container orchestration deployment",
    "expected_titles": ["kubernetes-setup.md", "docker-basics.md"],
    "type": "synonym"
  },
  {
    "query": "secure my server from attacks",
    "expected_titles": ["fail2ban-setup.md", "ssh-key-management.md"],
    "type": "cross_domain"
  }
]
```

Query types: direct match, synonym/paraphrase, cross-domain reasoning, negative distinction, ambiguous.

**Note:** The existing `evaluate_semantic_precision()` function in `repository.py` expects `expected_ids` (integer doc IDs). Since IDs are non-deterministic in a temp DB, the test cases use `expected_titles` instead. The test maps titles to IDs after scanning fixtures.

---

## Test Methods (7)

| # | Method | What it validates | KPI target |
|---|--------|-------------------|------------|
| 1 | `test_embedding_model_is_real` | sentence-transformers loaded, not hash fallback | model != `token-hash-v1`, dim == 384 |
| 2 | `test_precision_at_5_meets_target` | Semantic search returns relevant docs in top 5 | avg precision@5 >= 0.9 |
| 3 | `test_search_latency_p95_under_threshold` | Search completes within performance target | p95 < 150ms (10 runs per query) |
| 4 | `test_embedding_generation_throughput` | Embedding generation speed is adequate | 25 docs < 30s |
| 5 | `test_chunk_level_similarity_contributes` | Multi-signal ranking uses chunk scores | chunk score > 0 for targeted query |
| 6 | `test_api_round_trip_query` | Full HTTP stack returns consistent results | HTTP results match direct query results |
| 7 | `test_negative_distinction` | Unrelated docs not surfaced for specific queries | irrelevant docs below score threshold |

### setUpClass flow:
1. Create `tempfile.TemporaryDirectory`
2. Initialize database
3. Scan all 25 fixtures via `upsert_document()`
4. Generate embeddings for all documents
5. Record setup timing for throughput test

### test_api_round_trip_query detail:
- Start `ThreadingHTTPServer` on a random port in a daemon thread
- POST to `/api/v1/query` with `semantic_query` method
- Assert response matches direct `semantic_search_documents()` results
- Server shut down in `tearDownClass`

---

## Runner Script

`scripts/run-integration-tests.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "Checking ML dependencies..."
python -c "import sentence_transformers" 2>/dev/null || {
    echo "ERROR: sentence-transformers not installed."
    echo "Integration tests require the devcontainer environment."
    exit 1
}
python -c "import faiss" 2>/dev/null || {
    echo "WARNING: faiss-cpu not installed. FAISS tests will use brute-force fallback."
}

echo "Running integration tests..."
python -m pytest tests/integration/ -v --tb=short "$@"
```

---

## Files Created

| File | Purpose |
|------|---------|
| `tests/integration/__init__.py` | Package marker |
| `tests/integration/test_semantic_quality.py` | 7 test methods |
| `tests/integration/semantic_cases.json` | ~15 query cases |
| `tests/integration/fixtures/*.md` | 25 curated markdown files |
| `scripts/run-integration-tests.sh` | Dependency gate + runner |

## Files Modified

| File | Change |
|------|--------|
| `CLAUDE.md` | Add integration test run commands |

---

## Verification

After implementation, validate in the devcontainer:

```bash
# 1. Check ML dependencies available
python -c "import sentence_transformers; print('OK')"
python -c "import faiss; print('OK')"

# 2. Run the integration suite
bash scripts/run-integration-tests.sh

# 3. Verify all 7 tests pass
# Expected: 7 passed, 0 failed

# 4. Check output includes KPI metrics
# Should print precision@5 average, p95 latency, throughput
```
