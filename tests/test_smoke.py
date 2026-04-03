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
            shutil.copytree(FIXTURE_DIR, data_dir)

            env = os.environ.copy()
            env["COGNITIVE_ETL_DATA_DIR"] = str(data_dir)
            env["COGNITIVE_ETL_DIST_DIR"] = str(dist_dir)

            result = self.run_command("scripts/build_site.py", env=env)

            self.assertIn("Built to", result.stdout)
            self.assertTrue((dist_dir / "index.html").exists())
            self.assertTrue((dist_dir / "graph.html").exists())
            self.assertTrue((dist_dir / "atoms.html").exists())

            search_index = json.loads((dist_dir / "data" / "search_index.json").read_text(encoding="utf-8"))
            self.assertEqual(len(search_index), 4)

    def test_sync_help_is_available(self) -> None:
        result = self.run_command("scripts/sync_notion.py", "--help")
        self.assertIn("Sync Cognitive ETL data from Notion.", result.stdout)


if __name__ == "__main__":
    unittest.main()

