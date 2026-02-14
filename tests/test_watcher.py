from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import sqlite3
import tempfile
import time
import unittest

from markdownkeeper.storage.repository import list_documents
from markdownkeeper.storage.schema import initialize_database
from markdownkeeper.watcher.service import (
    _MarkdownWatchEventHandler,
    _drain_event_queue,
    _flush_pending_events,
    _queue_events,
    _snapshot,
    is_watchdog_available,
    watch_loop,
    watch_once,
)


class WatcherTests(unittest.TestCase):
    def test_watch_once_detects_create_modify_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir(parents=True, exist_ok=True)
            db = root / ".markdownkeeper" / "index.db"
            initialize_database(db)

            snap, r1 = watch_once(db, [docs], [".md"], None)
            self.assertEqual((r1.created, r1.modified, r1.deleted), (0, 0, 0))

            file = docs / "a.md"
            file.write_text("# A", encoding="utf-8")
            snap, r2 = watch_once(db, [docs], [".md"], snap)
            self.assertEqual(r2.created, 1)

            time.sleep(0.02)
            file.write_text("# A\nupdated", encoding="utf-8")
            snap, r3 = watch_once(db, [docs], [".md"], snap)
            self.assertEqual(r3.modified, 1)

            file.unlink()
            _, r4 = watch_once(db, [docs], [".md"], snap)
            self.assertEqual(r4.deleted, 1)
            self.assertEqual(len(list_documents(db)), 0)


    def test_flush_pending_events_indexes_and_deletes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir(parents=True, exist_ok=True)
            db = root / ".markdownkeeper" / "index.db"
            initialize_database(db)

            existing = docs / "existing.md"
            existing.write_text("# Existing", encoding="utf-8")
            snap, _ = watch_once(db, [docs], [".md"], None)
            self.assertIn(existing.resolve(), snap)

            created = docs / "new.md"
            created.write_text("# New", encoding="utf-8")
            existing.unlink()

            handler = _MarkdownWatchEventHandler({".md"})
            handler._record_change(str(created))
            handler._record_delete(str(existing))

            result = _flush_pending_events(db, handler)
            self.assertEqual(result.created + result.modified, 1)
            self.assertEqual(result.deleted, 1)

            docs_now = list_documents(db)
            self.assertEqual(len(docs_now), 1)
            self.assertTrue(docs_now[0].path.endswith("new.md"))


    def test_queue_replay_processes_persisted_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir(parents=True, exist_ok=True)
            db = root / ".markdownkeeper" / "index.db"
            initialize_database(db)

            file = docs / "queued.md"
            file.write_text("# Queued", encoding="utf-8")
            _queue_events(db, changed_paths=[file.resolve()], deleted_paths=[])

            # Simulate restart: queue row exists before draining.
            with sqlite3.connect(db) as connection:
                count = int(connection.execute("SELECT COUNT(*) FROM events WHERE status='queued'").fetchone()[0])
            self.assertEqual(count, 1)

            result = _drain_event_queue(db)
            self.assertEqual(result.created, 1)
            docs_now = list_documents(db)
            self.assertEqual(len(docs_now), 1)
            self.assertTrue(docs_now[0].path.endswith("queued.md"))

    def test_queue_coalesces_conflicting_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir(parents=True, exist_ok=True)
            db = root / ".markdownkeeper" / "index.db"
            initialize_database(db)

            file = docs / "flip.md"
            file.write_text("# Flip", encoding="utf-8")
            _queue_events(db, changed_paths=[file.resolve()], deleted_paths=[])
            _queue_events(db, changed_paths=[], deleted_paths=[file.resolve()])

            with sqlite3.connect(db) as connection:
                row = connection.execute(
                    "SELECT event_type FROM events WHERE status='queued' ORDER BY id DESC LIMIT 1"
                ).fetchone()
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(str(row[0]), "delete")


    def test_rapid_changes_are_restart_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir(parents=True, exist_ok=True)
            db = root / ".markdownkeeper" / "index.db"
            initialize_database(db)

            files: list[Path] = []
            for idx in range(40):
                file = docs / f"doc-{idx}.md"
                file.write_text(f"# Doc {idx}\nfirst", encoding="utf-8")
                files.append(file)

            _queue_events(db, changed_paths=[file.resolve() for file in files], deleted_paths=[])

            # Simulate burst updates before the queue is drained (as if process restarts later).
            for idx, file in enumerate(files[:20]):
                file.write_text(f"# Doc {idx}\nupdated", encoding="utf-8")
            _queue_events(db, changed_paths=[file.resolve() for file in files[:20]], deleted_paths=[])

            # Confirm pending queued work exists pre-drain.
            with sqlite3.connect(db) as connection:
                queued = int(connection.execute("SELECT COUNT(*) FROM events WHERE status='queued'").fetchone()[0])
            self.assertGreater(queued, 0)

            result = _drain_event_queue(db)
            self.assertEqual(result.created + result.modified, 40)

            indexed = list_documents(db)
            self.assertEqual(len(indexed), 40)

            with sqlite3.connect(db) as connection:
                remaining = int(connection.execute("SELECT COUNT(*) FROM events WHERE status='queued'").fetchone()[0])
                failed = int(connection.execute("SELECT COUNT(*) FROM events WHERE status='failed'").fetchone()[0])
            self.assertEqual(remaining, 0)
            self.assertEqual(failed, 0)

    def test_snapshot_only_includes_matching_extensions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.md").write_text("# Markdown", encoding="utf-8")
            (root / "b.txt").write_text("plain text", encoding="utf-8")
            (root / "c.markdown").write_text("# Also markdown", encoding="utf-8")

            snap = _snapshot([root], {".md", ".markdown"})
            resolved_names = {p.name for p in snap}
            self.assertIn("a.md", resolved_names)
            self.assertIn("c.markdown", resolved_names)
            self.assertNotIn("b.txt", resolved_names)

    def test_snapshot_skips_nonexistent_roots(self) -> None:
        snap = _snapshot([Path("/nonexistent/path/xyz")], {".md"})
        self.assertEqual(snap, {})

    def test_snapshot_recursive_finds_nested_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "sub" / "deep"
            nested.mkdir(parents=True)
            (nested / "doc.md").write_text("# Nested", encoding="utf-8")

            snap = _snapshot([root], {".md"})
            self.assertEqual(len(snap), 1)

    def test_is_watchdog_available_returns_bool(self) -> None:
        result = is_watchdog_available()
        self.assertIsInstance(result, bool)

    def test_watch_loop_with_one_iteration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir(parents=True, exist_ok=True)
            db = root / ".markdownkeeper" / "index.db"
            initialize_database(db)

            (docs / "a.md").write_text("# Doc A", encoding="utf-8")
            result = watch_loop(db, [docs], [".md"], interval_s=0.05, iterations=1)
            self.assertEqual(result.created, 1)
            self.assertEqual(len(list_documents(db)), 1)

    def test_handler_on_moved_records_delete_and_create(self) -> None:
        handler = _MarkdownWatchEventHandler({".md"})

        class FakeEvent:
            def __init__(self, src: str, dest: str = "", is_dir: bool = False):
                self.src_path = src
                self.dest_path = dest
                self.is_directory = is_dir

        handler.on_moved(FakeEvent("/tmp/old.md", "/tmp/new.md"))
        self.assertEqual(len(handler.deleted), 1)
        self.assertEqual(len(handler.changed), 1)

    def test_handler_ignores_directory_events(self) -> None:
        handler = _MarkdownWatchEventHandler({".md"})

        class FakeEvent:
            def __init__(self, src: str, is_dir: bool = False):
                self.src_path = src
                self.is_directory = is_dir

        handler.on_created(FakeEvent("/tmp/subdir", is_dir=True))
        handler.on_modified(FakeEvent("/tmp/subdir", is_dir=True))
        handler.on_deleted(FakeEvent("/tmp/subdir", is_dir=True))
        self.assertEqual(len(handler.changed), 0)
        self.assertEqual(len(handler.deleted), 0)

    def test_handler_ignores_non_markdown_files(self) -> None:
        handler = _MarkdownWatchEventHandler({".md"})

        class FakeEvent:
            def __init__(self, src: str, is_dir: bool = False):
                self.src_path = src
                self.is_directory = is_dir

        handler.on_created(FakeEvent("/tmp/file.txt"))
        handler.on_modified(FakeEvent("/tmp/file.py"))
        self.assertEqual(len(handler.changed), 0)

    def test_drain_empty_queue_returns_zero_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / ".markdownkeeper" / "index.db"
            initialize_database(db)
            result = _drain_event_queue(db)
            self.assertEqual(result.created, 0)
            self.assertEqual(result.modified, 0)
            self.assertEqual(result.deleted, 0)

    def test_queue_events_empty_lists_does_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / ".markdownkeeper" / "index.db"
            initialize_database(db)
            _queue_events(db, changed_paths=[], deleted_paths=[])
            with sqlite3.connect(db) as conn:
                count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
