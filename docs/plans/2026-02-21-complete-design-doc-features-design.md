# Design: Complete Design Document Feature Set

**Date:** 2026-02-21
**Status:** Approved
**Approach:** Bottom-up by dependency (sequential, each step builds on the last)

## Scope

Implement all 7 items identified in the codebase review as gaps between the Project Design Document and the current implementation.

## Items

### 1. Bug Fix: Watchdog --iterations Ignored

**Problem:** `--mode auto` selects watchdog when available, but `watch_loop_watchdog` ignores `--iterations` and loops forever without `--duration`.

**Fix:** In `_handle_watch`, when watchdog mode is selected and `args.iterations` is set but `args.duration` is not, derive `duration_s = args.iterations * args.interval`. Emit a stderr warning that `--iterations` is approximate in watchdog mode.

**Files:** `cli/main.py`
**Tests:** Fix hanging test, add watchdog-duration-derivation test.

### 2. Metadata Module

**Problem:** `metadata/__init__.py` is stub-only.

**Design:** Create `metadata/manager.py` with:

- `enforce_schema(parsed, required_fields) -> list[str]` — returns violations
- `auto_fill(parsed, filepath) -> dict` — generates missing metadata (created, modified, category, token_count)
- `extract_concepts(text) -> list[str]` — term-frequency concept extraction from body text when frontmatter has none

Read-only on source docs. Produces metadata for DB storage only.

**Config:** Add `required_frontmatter_fields` list.
**Files:** `metadata/manager.py`, `config.py`
**Tests:** Schema validation, auto-fill, concept extraction.

### 3. Auto-Summarization

**Problem:** Summaries only come from frontmatter. Documents without it have empty summaries.

**Design:** Create `metadata/summarizer.py` with:

- `generate_summary(parsed, max_tokens=150) -> str`
  - Frontmatter summary preserved if present
  - Otherwise: `"{title}. Covers: {h2_1}, {h2_2}, ... {first_paragraph_truncated}"`
  - Truncate to max_tokens

**Integration:** Call in `upsert_document` when parsed doc has no frontmatter summary.
**Files:** `metadata/summarizer.py`, `storage/repository.py`
**Tests:** Frontmatter preserved, generated when missing, truncation, empty doc edge case.

### 4. External Link Validation

**Problem:** `links/validator.py` only checks internal links.

**Design:** Extend validator with:

- `_check_external(target, timeout=10) -> str` — HTTP HEAD via `urllib.request`, fallback to GET on 405. Returns "ok"/"broken"/"timeout".
- Per-domain rate limiting: 1s delay between requests to same host.
- `validate_links(db_path, check_external=False)` — opt-in parameter.
- CLI: `--check-external` flag on `check-links` command.

**Dependencies:** None (stdlib urllib).
**Files:** `links/validator.py`, `cli/main.py`
**Tests:** Mock HTTP ok/404/timeout/405, rate limiter, integration.

### 5. Query Result Caching

**Problem:** `query_cache` table exists but is unused.

**Design:** Add caching in `storage/repository.py`:

- Cache key: SHA256 of normalized (query, limit, mode)
- Write after search execution
- Read before search execution; return if within TTL
- Invalidation: full flush on `upsert_document` / `delete_document_by_path`
- Track `hit_count` for observability

**Config:** `cache_ttl_seconds` (default 3600), `cache_enabled` (default true).
**Files:** `storage/repository.py`, `config.py`
**Tests:** Miss→populate, hit returns cached, invalidation on upsert, TTL expiry, stats hit_count.

### 6. FAISS Index (Optional)

**Problem:** Semantic search is O(n) brute-force cosine.

**Design:** Create `query/faiss_index.py` with `FaissIndex` class:

- `build(embeddings)` — flat L2 index
- `search(query_vector, k)` — top-k results
- `save(path)` / `load(path)` — persist to `.markdownkeeper/faiss.index`

Optional dependency (mirrors sentence-transformers pattern). Falls back to brute-force when not installed. Rebuilt by `embeddings-generate` command.

**Config:** `faiss_enabled` (default true), `faiss_index_path`.
**pyproject.toml:** Add `faiss = ["faiss-cpu>=1.7"]` optional dependency.
**Files:** `query/faiss_index.py`, `storage/repository.py`, `cli/main.py`, `pyproject.toml`
**Tests:** Build, search, fallback, persistence.

### 7. `mdkeeper report` Command

**Problem:** No health report command.

**Design:** Add `generate_health_report(db_path) -> dict` in repository:

- Aggregate queries: document count, total tokens, broken links by type, missing summaries, embedding coverage, cache stats, event queue status
- CLI: `mdkeeper report [--format text|json]`
- Text output renders as bordered table

Capstone feature — exercises data from all other items.

**Files:** `storage/repository.py`, `cli/main.py`
**Tests:** Populated DB, empty DB, JSON format.

## Dependency Order

```
1. Bug fix (unblocks test suite)
   └─> 2. Metadata module (foundational)
       └─> 3. Auto-summarization (builds on metadata)
4. External link validation (independent)
5. Query result caching (independent)
6. FAISS index (independent, optional)
7. Report command (aggregates all above)
```

Items 4-6 are independent of each other but should follow items 1-3. Item 7 is last as the capstone.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Summarization strategy | Heading + first-paragraph extraction | Zero external deps, captures document intent, deterministic |
| FAISS dependency | Optional (like sentence-transformers) | Best of both worlds: performance when installed, no hard requirement |
| External HTTP client | stdlib urllib.request | Avoids adding requests/aiohttp as hard dependencies |
| Cache invalidation | Full flush on doc changes | Simple, correct; docs change infrequently vs queries |
| Implementation order | Bottom-up by dependency | Each step testable, later features build on earlier ones |
