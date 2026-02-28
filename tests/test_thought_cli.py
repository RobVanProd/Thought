import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

import thought_cli


class TestThoughtCli(unittest.TestCase):
    def _new_db_path(self, prefix: str) -> Path:
        Path("results").mkdir(parents=True, exist_ok=True)
        return Path("results") / f"{prefix}_{uuid4().hex}.sqlite"

    def _cleanup(self, path: Path) -> None:
        if path.exists():
            path.unlink()

    def _run_cli(self, argv: list[str]) -> tuple[int, str]:
        buffer = io.StringIO()
        with patch("sys.argv", argv):
            with redirect_stdout(buffer):
                code = thought_cli.main()
        return code, buffer.getvalue()

    def test_store_and_retrieve(self) -> None:
        db = self._new_db_path("cli_store")
        try:
            store_cmd = [
                "thought_cli.py",
                "--db",
                str(db),
                "--embed-dim",
                "32",
                "store",
                "--session",
                "s_cli",
                "--raw-text",
                "Intro /thought[collect logs] done.",
            ]
            code, out = self._run_cli(store_cmd)
            self.assertEqual(code, 0)
            payload = json.loads(out)
            self.assertGreaterEqual(payload["stored"], 1)

            retrieve_cmd = [
                "thought_cli.py",
                "--db",
                str(db),
                "--embed-dim",
                "32",
                "retrieve",
                "--query",
                "collect logs",
                "--session",
                "s_cli",
                "--limit",
                "5",
            ]
            code2, out2 = self._run_cli(retrieve_cmd)
            self.assertEqual(code2, 0)
            hits = json.loads(out2)
            self.assertTrue(hits)
        finally:
            self._cleanup(db)

    def test_loop_and_reflect_commands(self) -> None:
        db = self._new_db_path("cli_loop")
        try:
            loop_cmd = [
                "thought_cli.py",
                "--db",
                str(db),
                "--embed-dim",
                "24",
                "loop",
                "--session",
                "loop_session",
                "--input",
                "assess rollout safety",
            ]
            code, out = self._run_cli(loop_cmd)
            self.assertEqual(code, 0)
            loop_payload = json.loads(out)
            self.assertTrue(loop_payload["reflected"])

            reflect_cmd = [
                "thought_cli.py",
                "--db",
                str(db),
                "--embed-dim",
                "24",
                "reflect",
                "--query",
                "rollout safety",
                "--session",
                "loop_session",
                "--mode",
                "reasoning",
            ]
            code2, out2 = self._run_cli(reflect_cmd)
            self.assertEqual(code2, 0)
            reflect_payload = json.loads(out2)
            self.assertGreaterEqual(reflect_payload["stored_reflections"], 1)
        finally:
            self._cleanup(db)

    def test_import_jsonl(self) -> None:
        db = self._new_db_path("cli_import")
        data = Path("results") / f"cli_import_{uuid4().hex}.jsonl"
        try:
            rows = [
                {"session_id": "s1", "raw_output": "A /thought[first] B", "category": "reasoning", "tags": ["a"]},
                {"session_id": "s2", "raw_output": "C /thought[second] D", "category": "plan", "tags": ["b"]},
            ]
            data.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

            cmd = [
                "thought_cli.py",
                "--db",
                str(db),
                "--embed-dim",
                "16",
                "import-jsonl",
                "--path",
                str(data),
            ]
            code, out = self._run_cli(cmd)
            self.assertEqual(code, 0)
            payload = json.loads(out)
            self.assertEqual(payload["imported_thoughts"], 2)
        finally:
            self._cleanup(db)
            self._cleanup(data)

    def test_store_requires_input(self) -> None:
        db = self._new_db_path("cli_err")
        try:
            cmd = [
                "thought_cli.py",
                "--db",
                str(db),
                "store",
                "--session",
                "s",
            ]
            with self.assertRaises(ValueError):
                self._run_cli(cmd)
        finally:
            self._cleanup(db)


if __name__ == "__main__":
    unittest.main()
