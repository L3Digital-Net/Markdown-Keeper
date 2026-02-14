from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import sqlite3
import tempfile
import unittest

from markdownkeeper.links.validator import _check_internal, validate_links
from markdownkeeper.processor.parser import parse_markdown
from markdownkeeper.storage.repository import upsert_document
from markdownkeeper.storage.schema import initialize_database


class LinkValidatorTests(unittest.TestCase):
    def test_validate_links_marks_internal_ok_and_broken(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = tmp_path / ".markdownkeeper" / "index.db"
            docs = tmp_path / "docs"
            docs.mkdir(parents=True, exist_ok=True)
            target = docs / "exists.md"
            target.write_text("# Exists", encoding="utf-8")

            source = docs / "source.md"
            source.write_text("# S\n[good](./exists.md) [bad](./missing.md)", encoding="utf-8")

            initialize_database(db_path)
            upsert_document(db_path, source, parse_markdown(source.read_text(encoding="utf-8")))

            results = validate_links(db_path)
            statuses = {item.target: item.status for item in results}
            self.assertEqual(statuses["./exists.md"], "ok")
            self.assertEqual(statuses["./missing.md"], "broken")

            with sqlite3.connect(db_path) as connection:
                rows = connection.execute("SELECT target, status, checked_at FROM links").fetchall()
            self.assertTrue(all(row[2] for row in rows))

    def test_check_internal_hash_only_anchor_returns_ok(self) -> None:
        result = _check_internal("/some/doc.md", "#section")
        self.assertEqual(result, "ok")

    def test_check_internal_empty_target_returns_ok(self) -> None:
        result = _check_internal("/some/doc.md", "")
        self.assertEqual(result, "ok")

    def test_check_internal_with_anchor_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "doc.md"
            doc.write_text("# Doc", encoding="utf-8")
            target_file = Path(tmp) / "target.md"
            target_file.write_text("# Target", encoding="utf-8")
            result = _check_internal(str(doc), "target.md#section")
            self.assertEqual(result, "ok")

    def test_validate_links_empty_database_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / ".markdownkeeper" / "index.db"
            initialize_database(db_path)
            results = validate_links(db_path)
            self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
