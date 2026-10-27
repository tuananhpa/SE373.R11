import json
import tempfile
import unittest
from pathlib import Path
from memory import MemoryStore
from agent import run_session, ScriptedModel

class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_replacement_survives_new_store(self):
        store = MemoryStore(self.root / "memory.json")
        old = store.remember("auth", "JWT", "Hãy nhớ dùng JWT.", "s1", "JWT")
        new = store.remember("auth", "session cookie thay JWT", "Chuyển sang session cookie thay JWT.", "s3", "session cookie thay JWT")
        loaded = MemoryStore(store.path)
        self.assertEqual([r["value"] for r in loaded.active()], ["session cookie thay JWT"])
        self.assertEqual(loaded.records()[0]["superseded_by"], new["id"])
        self.assertEqual(loaded.records()[0]["id"], old["id"])

    def test_bad_evidence_does_not_write(self):
        store = MemoryStore(self.root / "memory.json")
        with self.assertRaises(ValueError):
            store.remember("auth", "JWT", "Dự án dùng cookie.", "s", "JWT")
        self.assertFalse(store.path.exists())

    def test_corrupt_store_is_not_silently_reset(self):
        path = self.root / "memory.json"
        path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(ValueError):
            MemoryStore(path).active()
        self.assertEqual(path.read_text(), "{broken")

    def test_read_only_session_and_disabled_control(self):
        path = self.root / "memory.json"
        MemoryStore(path).remember("auth", "JWT", "Nhớ JWT", "s1", "JWT")
        model = ScriptedModel([{"tool":"read_memory"}, {"tool":"final","answer":"JWT"}])
        result = run_session("Auth?", path, self.root / "s2", model)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["history_messages"], 0)
        self.assertEqual(result["injected_memory"][0]["value"], "JWT")
        result = run_session("Auth?", path, self.root / "control",
                             ScriptedModel([{"tool":"final","answer":"Chưa biết"}]), False)
        self.assertEqual(result["injected_memory"], [])
        self.assertEqual(result["usage"], None)

    def test_disabled_tools_and_step_limit_fail(self):
        for enabled, actions in [(False,[{"tool":"read_memory"}]),
                                 (True,[{"tool":"read_memory"}] * 6)]:
            result = run_session("?", self.root / "memory.json", self.root / str(enabled),
                                 ScriptedModel(actions), enabled)
            self.assertEqual(result["status"], "failed")

    def test_write_then_failure_keeps_record_and_trace(self):
        result = run_session("Hãy nhớ JWT", self.root / "memory.json", self.root / "s",
            ScriptedModel([{"tool":"remember_memory","key":"auth","value":"JWT","evidence":"JWT"},
                           {"tool":"unknown"}]))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(MemoryStore(self.root / "memory.json").active()[0]["value"], "JWT")
        self.assertEqual(len(result["trace"]), 1)

if __name__ == "__main__":
    unittest.main()
