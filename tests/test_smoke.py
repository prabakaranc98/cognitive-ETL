from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT_DIR / "tests" / "fixtures" / "sample_data"
sys.path.insert(0, str(ROOT_DIR / "src"))

from cognitive_etl.site_builder import normalize_public_url


class SmokeTests(unittest.TestCase):
    def run_command(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *args],
            cwd=ROOT_DIR,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_build_site_with_sample_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_root = Path(tmp_dir)
            data_dir = temp_root / "data"
            dist_dir = temp_root / "dist"
            content_dir = temp_root / "content"
            shutil.copytree(FIXTURE_DIR, data_dir)

            env = os.environ.copy()
            env["COGNITIVE_ETL_DATA_DIR"] = str(data_dir)
            env["COGNITIVE_ETL_DIST_DIR"] = str(dist_dir)
            env["COGNITIVE_ETL_CONTENT_DIR"] = str(content_dir)

            result = self.run_command("scripts/build_site.py", env=env)

            self.assertIn("Built to", result.stdout)
            self.assertTrue((dist_dir / "index.html").exists())
            self.assertTrue((dist_dir / "captures.html").exists())
            self.assertTrue((dist_dir / "graph.html").exists())
            self.assertTrue((dist_dir / "atoms.html").exists())
            self.assertTrue((dist_dir / "source-src-1.html").exists())
            self.assertTrue((dist_dir / "capture-cap-1.html").exists())
            self.assertTrue((dist_dir / "atom-atm-1.html").exists())
            self.assertTrue((dist_dir / "artifact-art-1.html").exists())
            self.assertTrue((content_dir / "README.md").exists())
            self.assertTrue(any((content_dir / "sources").glob("*.md")))
            self.assertTrue(any((content_dir / "captures").glob("*.md")))
            self.assertTrue(any((content_dir / "atoms").glob("*.md")))
            self.assertTrue(any((content_dir / "artifacts").glob("*.md")))

            search_index = json.loads((dist_dir / "data" / "search_index.json").read_text(encoding="utf-8"))
            self.assertEqual(len(search_index), 5)
            self.assertIn("capture-cap-1.html", {item["href"] for item in search_index})
            self.assertIn("atom-atm-1.html", {item["href"] for item in search_index})

    def test_sync_help_is_available(self) -> None:
        result = self.run_command("scripts/sync_notion.py", "--help")
        self.assertIn("Sync Cognitive ETL data from Notion.", result.stdout)

    def test_public_link_filter(self) -> None:
        self.assertEqual(normalize_public_url("https://www.notion.so/private-page"), "")
        self.assertEqual(
            normalize_public_url("https://example.notion.site/public-page"),
            "https://example.notion.site/public-page",
        )
        self.assertEqual(
            normalize_public_url("https://gist.github.com/example/abc123"),
            "https://gist.github.com/example/abc123",
        )


if __name__ == "__main__":
    unittest.main()
