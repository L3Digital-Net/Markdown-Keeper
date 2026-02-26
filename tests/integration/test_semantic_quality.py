"""Integration tests for semantic search quality.

Requires sentence-transformers and faiss-cpu (devcontainer environment).
Run via: bash scripts/run-integration-tests.sh

Validates KPIs from the Project Design Document:
  - precision@5 >= 0.9
  - semantic search latency p95 < 150ms
  - embedding generation throughput: 25 docs < 30s
"""
from __future__ import annotations

import json
import statistics
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

# Ensure src/ is importable (matches project test convention)
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from markdownkeeper.api.server import build_handler
from markdownkeeper.processor.parser import parse_markdown
from markdownkeeper.query.embeddings import compute_embedding
from markdownkeeper.storage.repository import semantic_search_documents, upsert_document
from markdownkeeper.storage.schema import initialize_database

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
CASES_FILE = Path(__file__).resolve().parent / "semantic_cases.json"

# KPI thresholds from Project Design Document
PRECISION_AT_5_TARGET = 0.9
LATENCY_P95_MS = 150.0
THROUGHPUT_TIMEOUT_S = 30.0


def _load_cases() -> list[dict[str, Any]]:
    with open(CASES_FILE) as f:
        return json.load(f)


class SemanticQualityTests(unittest.TestCase):
    """Validate ML-powered semantic search against v1.0.0 KPI targets."""

    db_path: Path
    _tmpdir: tempfile.TemporaryDirectory[str]
    _title_to_id: dict[str, int]
    _setup_duration_s: float
    _server: ThreadingHTTPServer
    _server_port: int

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.TemporaryDirectory()
        tmp = Path(cls._tmpdir.name)
        cls.db_path = tmp / "test.db"
        initialize_database(cls.db_path)

        # Scan all fixtures and build title-to-ID mapping
        cls._title_to_id = {}
        start = time.perf_counter()

        fixture_files = sorted(FIXTURES_DIR.glob("*.md"))
        if not fixture_files:
            raise RuntimeError(f"No fixture files found in {FIXTURES_DIR}")

        for md_file in fixture_files:
            text = md_file.read_text(encoding="utf-8")
            parsed = parse_markdown(text)
            doc_id = upsert_document(cls.db_path, md_file, parsed)
            cls._title_to_id[md_file.name] = doc_id

        cls._setup_duration_s = time.perf_counter() - start

        # Start API server on a random port for the round-trip test
        handler = build_handler(cls.db_path)
        cls._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls._server_port = cls._server.server_address[1]
        thread = threading.Thread(target=cls._server.serve_forever, daemon=True)
        thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._server.shutdown()
        cls._tmpdir.cleanup()

    # -- Test 1: Embedding model verification --

    def test_embedding_model_is_real(self) -> None:
        """Verify sentence-transformers is loaded, not the hash fallback."""
        vector, model_name = compute_embedding("test embedding quality")
        self.assertNotEqual(model_name, "token-hash-v1",
                            "Expected real ML model but got hash fallback. "
                            "Is sentence-transformers installed?")
        self.assertEqual(len(vector), 384,
                         f"Expected 384-dim MiniLM vector, got {len(vector)}-dim")

    # -- Test 2: Precision@5 --

    def test_precision_at_5_meets_target(self) -> None:
        """Average precision@5 across all query cases must meet KPI target."""
        cases = _load_cases()
        precisions: list[float] = []

        for case in cases:
            query = case["query"]
            expected_titles = case["expected_titles"]
            expected_ids = {self._title_to_id[t] for t in expected_titles
                           if t in self._title_to_id}

            results = semantic_search_documents(self.db_path, query, limit=5)
            result_ids = {r.id for r in results[:5]}
            hits = len(expected_ids & result_ids)
            precision = hits / max(1, len(expected_ids))
            precisions.append(precision)

        avg_precision = sum(precisions) / len(precisions)
        print(f"\n  precision@5 average: {avg_precision:.3f} "
              f"(target: {PRECISION_AT_5_TARGET})")
        print(f"  per-case: {[f'{p:.2f}' for p in precisions]}")

        self.assertGreaterEqual(avg_precision, PRECISION_AT_5_TARGET,
                                f"Average precision@5 {avg_precision:.3f} "
                                f"below target {PRECISION_AT_5_TARGET}")

    # -- Test 3: Search latency p95 --

    def test_search_latency_p95_under_threshold(self) -> None:
        """p95 semantic search latency must stay under the KPI threshold."""
        cases = _load_cases()
        latencies_ms: list[float] = []

        # 10 runs per query to get stable latency distribution
        for _ in range(10):
            for case in cases:
                start = time.perf_counter()
                semantic_search_documents(self.db_path, case["query"], limit=5)
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                latencies_ms.append(elapsed_ms)

        sorted_lat = sorted(latencies_ms)
        p50 = statistics.median(sorted_lat)
        p95_index = min(len(sorted_lat) - 1,
                        int(round(0.95 * (len(sorted_lat) - 1))))
        p95 = sorted_lat[p95_index]

        print(f"\n  latency p50: {p50:.1f}ms  p95: {p95:.1f}ms  "
              f"max: {max(sorted_lat):.1f}ms  (target p95: {LATENCY_P95_MS}ms)")

        self.assertLess(p95, LATENCY_P95_MS,
                        f"p95 latency {p95:.1f}ms exceeds target {LATENCY_P95_MS}ms")

    # -- Test 4: Embedding generation throughput --

    def test_embedding_generation_throughput(self) -> None:
        """All 25 fixtures must be scanned and embedded within the timeout."""
        fixture_count = len(list(FIXTURES_DIR.glob("*.md")))
        print(f"\n  {fixture_count} docs ingested + embedded in "
              f"{self._setup_duration_s:.2f}s "
              f"(limit: {THROUGHPUT_TIMEOUT_S}s)")

        self.assertLess(self._setup_duration_s, THROUGHPUT_TIMEOUT_S,
                        f"Setup took {self._setup_duration_s:.1f}s, "
                        f"exceeds {THROUGHPUT_TIMEOUT_S}s limit")

    # -- Test 5: Chunk-level similarity contributes to ranking --

    def test_chunk_level_similarity_contributes(self) -> None:
        """A query targeting a specific paragraph should benefit from chunk scoring."""
        # Use a query that matches a specific section, not just the title
        results = semantic_search_documents(
            self.db_path, "pg_dump full database backup with compression", limit=5
        )
        # postgresql-backup.md should rank high due to chunk-level match
        pg_id = self._title_to_id.get("postgresql-backup.md")
        self.assertIsNotNone(pg_id, "postgresql-backup.md not in fixtures")
        result_ids = [r.id for r in results[:5]]
        self.assertIn(pg_id, result_ids,
                      f"postgresql-backup.md (id={pg_id}) not in top 5 for "
                      f"chunk-specific query. Got: {result_ids}")

    # -- Test 6: API round-trip --

    def test_api_round_trip_query(self) -> None:
        """Semantic query through the HTTP API should return consistent results."""
        query = "kubernetes cluster setup"

        # Direct query
        direct_results = semantic_search_documents(self.db_path, query, limit=5)
        direct_ids = [r.id for r in direct_results]

        # HTTP API query
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "semantic_query",
            "params": {"query": query, "max_results": 5}
        }).encode("utf-8")

        url = f"http://127.0.0.1:{self._server_port}/api/v1/query"
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        self.assertIn("result", body, f"API error: {body}")
        api_docs = body["result"]["documents"]
        api_ids = [doc["id"] for doc in api_docs]

        self.assertEqual(direct_ids, api_ids,
                         f"API results differ from direct query.\n"
                         f"  direct: {direct_ids}\n"
                         f"  api:    {api_ids}")

    # -- Test 7: Negative distinction --

    def test_negative_distinction(self) -> None:
        """Unrelated documents should not appear in top results for specific queries."""
        # Query about Python testing should NOT return sysadmin docs
        results = semantic_search_documents(
            self.db_path, "python pytest unit test fixtures mocking", limit=5
        )
        result_ids = {r.id for r in results}

        # These sysadmin docs should not appear for a Python testing query
        unrelated = ["zfs-pool-management.md", "dns-troubleshooting.md",
                      "fail2ban-setup.md", "postgresql-backup.md"]
        for title in unrelated:
            doc_id = self._title_to_id.get(title)
            if doc_id is not None:
                self.assertNotIn(doc_id, result_ids,
                                 f"{title} (id={doc_id}) should not appear in "
                                 f"top 5 for Python testing query")


if __name__ == "__main__":
    unittest.main()
