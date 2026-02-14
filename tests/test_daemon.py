from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import tempfile
import time
import unittest
import warnings

from markdownkeeper.daemon import reload_background, restart_background, start_background, status_background, stop_background, _read_pid, _is_pid_running


class DaemonTests(unittest.TestCase):
    def test_start_status_stop_background_process(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "watch.pid"
            cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                pid = start_background(cmd, pid_file)
            self.assertTrue(pid_file.exists())
            running, status_pid = status_background(pid_file)
            self.assertTrue(running)
            self.assertEqual(status_pid, pid)

            stopped = stop_background(pid_file, timeout_s=2.0)
            self.assertTrue(stopped)
            time.sleep(0.05)
            running2, _ = status_background(pid_file)
            self.assertFalse(running2)

    def test_restart_background_replaces_pid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "watch.pid"
            cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                first_pid = start_background(cmd, pid_file)
                second_pid = restart_background(cmd, pid_file, timeout_s=2.0)
            self.assertNotEqual(first_pid, second_pid)

            running, status_pid = status_background(pid_file)
            self.assertTrue(running)
            self.assertEqual(status_pid, second_pid)

            self.assertTrue(stop_background(pid_file, timeout_s=2.0))

    def test_reload_background_returns_false_for_missing_pid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "missing.pid"
            self.assertFalse(reload_background(pid_file))

    def test_read_pid_returns_none_for_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "empty.pid"
            pid_file.write_text("", encoding="utf-8")
            self.assertIsNone(_read_pid(pid_file))

    def test_read_pid_returns_none_for_invalid_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "bad.pid"
            pid_file.write_text("not_a_number", encoding="utf-8")
            self.assertIsNone(_read_pid(pid_file))

    def test_read_pid_returns_none_for_nonexistent_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "nope.pid"
            self.assertIsNone(_read_pid(pid_file))

    def test_is_pid_running_returns_false_for_dead_pid(self) -> None:
        self.assertFalse(_is_pid_running(999999999))

    def test_stop_background_returns_false_for_missing_pid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "none.pid"
            self.assertFalse(stop_background(pid_file))

    def test_stop_background_cleans_stale_pid_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "stale.pid"
            pid_file.write_text("999999999", encoding="utf-8")
            stopped = stop_background(pid_file)
            self.assertFalse(stopped)
            self.assertFalse(pid_file.exists())

    def test_status_background_returns_false_none_for_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "nope.pid"
            running, pid = status_background(pid_file)
            self.assertFalse(running)
            self.assertIsNone(pid)

    def test_start_background_returns_existing_pid_if_running(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "dup.pid"
            cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                pid1 = start_background(cmd, pid_file)
                pid2 = start_background(cmd, pid_file)
            self.assertEqual(pid1, pid2)
            stop_background(pid_file, timeout_s=2.0)


if __name__ == "__main__":
    unittest.main()
