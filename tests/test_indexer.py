from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import tempfile
import unittest

from markdownkeeper.indexer.generator import (
    generate_all_indexes,
    generate_master_index,
    generate_category_index,
    generate_tag_index,
    generate_concept_index,
)
from markdownkeeper.processor.parser import parse_markdown
from markdownkeeper.storage.repository import upsert_document
from markdownkeeper.storage.schema import initialize_database


class IndexerTests(unittest.TestCase):
    def test_generate_indexes_write_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / ".markdownkeeper" / "index.db"
            initialize_database(db)
            doc = root / "docs" / "a.md"
            doc.parent.mkdir(parents=True, exist_ok=True)
            doc.write_text(
                "---\ntags: api\ncategory: guides\nconcepts: kubernetes\n---\n# Alpha\nbody",
                encoding="utf-8",
            )
            upsert_document(db, doc, parse_markdown(doc.read_text(encoding="utf-8")))

            outs = generate_all_indexes(db, root / "_index")
            self.assertEqual(len(outs), 4)
            self.assertTrue((root / "_index" / "master.md").exists())
            self.assertTrue((root / "_index" / "by-category.md").exists())
            self.assertTrue((root / "_index" / "by-tag.md").exists())
            self.assertTrue((root / "_index" / "by-concept.md").exists())

    def test_master_index_empty_database_shows_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / ".markdownkeeper" / "index.db"
            initialize_database(db)
            out = generate_master_index(db, root / "_index")
            content = out.read_text(encoding="utf-8")
            self.assertIn("No indexed documents found", content)

    def test_category_index_empty_database_shows_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / ".markdownkeeper" / "index.db"
            initialize_database(db)
            out = generate_category_index(db, root / "_index")
            content = out.read_text(encoding="utf-8")
            self.assertIn("No indexed documents found", content)

    def test_tag_index_empty_database_shows_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / ".markdownkeeper" / "index.db"
            initialize_database(db)
            out = generate_tag_index(db, root / "_index")
            content = out.read_text(encoding="utf-8")
            self.assertIn("No tagged documents found", content)

    def test_concept_index_empty_database_shows_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / ".markdownkeeper" / "index.db"
            initialize_database(db)
            out = generate_concept_index(db, root / "_index")
            content = out.read_text(encoding="utf-8")
            self.assertIn("No concept mappings found", content)

    def test_master_index_includes_document_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / ".markdownkeeper" / "index.db"
            initialize_database(db)
            doc = root / "test.md"
            doc.write_text("# My Document\nThis is the summary content.", encoding="utf-8")
            upsert_document(db, doc, parse_markdown(doc.read_text(encoding="utf-8")))
            out = generate_master_index(db, root / "_index")
            content = out.read_text(encoding="utf-8")
            self.assertIn("My Document", content)


if __name__ == "__main__":
    unittest.main()
