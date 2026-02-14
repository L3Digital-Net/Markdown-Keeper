from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import tempfile
import unittest

from markdownkeeper.config import load_config


class ConfigTests(unittest.TestCase):
    def test_load_default_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "missing.toml"
            config = load_config(config_path)
            self.assertEqual(config.watch.debounce_ms, 500)
            self.assertEqual(config.storage.database_path, ".markdownkeeper/index.db")

    def test_load_custom_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "markdownkeeper.toml"
            config_path.write_text(
                """
[watch]
roots = ["docs", "runbooks"]
extensions = [".md"]
debounce_ms = 900

[storage]
database_path = "state/custom.db"

[api]
host = "0.0.0.0"
port = 9999
                """.strip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

            self.assertEqual(config.watch.roots, ["docs", "runbooks"])
            self.assertEqual(config.watch.extensions, [".md"])
            self.assertEqual(config.watch.debounce_ms, 900)
            self.assertEqual(config.storage.database_path, "state/custom.db")
            self.assertEqual(config.api.host, "0.0.0.0")
            self.assertEqual(config.api.port, 9999)

    def test_partial_config_falls_back_to_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "markdownkeeper.toml"
            config_path.write_text("[watch]\nroots=[\"docs\"]\n", encoding="utf-8")
            config = load_config(config_path)

            self.assertEqual(config.watch.roots, ["docs"])
            self.assertEqual(config.watch.extensions, [".md", ".markdown"])
            self.assertEqual(config.api.host, "127.0.0.1")

    def test_empty_config_file_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "markdownkeeper.toml"
            config_path.write_text("", encoding="utf-8")
            config = load_config(config_path)
            self.assertEqual(config.watch.debounce_ms, 500)
            self.assertEqual(config.api.port, 8765)

    def test_default_config_slots(self) -> None:
        from markdownkeeper.config import WatchConfig, StorageConfig, ApiConfig, AppConfig
        wc = WatchConfig()
        self.assertEqual(wc.roots, ["."])
        sc = StorageConfig()
        self.assertEqual(sc.database_path, ".markdownkeeper/index.db")
        ac = ApiConfig()
        self.assertEqual(ac.host, "127.0.0.1")
        app = AppConfig()
        self.assertIsInstance(app.watch, WatchConfig)
        self.assertIsInstance(app.storage, StorageConfig)
        self.assertIsInstance(app.api, ApiConfig)


if __name__ == "__main__":
    unittest.main()
