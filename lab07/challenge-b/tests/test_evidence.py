import json
import shutil
import tempfile
import unittest
from pathlib import Path
from demo import run_demo
from verify import verify

class EvidenceTests(unittest.TestCase):
    def test_portable_evidence_and_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = Path(tmp)/"original"
            moved = Path(tmp)/"moved"
            run_demo(original,False)
            shutil.copytree(original,moved)
            self.assertTrue(verify(moved)["passed"])
            path = moved/"b1"/"checkpoint.json"
            checkpoint = json.loads(path.read_text(encoding="utf-8"))
            checkpoint["next_action"] = "forget the task"
            path.write_text(json.dumps(checkpoint),encoding="utf-8")
            self.assertFalse(verify(moved)["passed"])

if __name__ == "__main__":
    unittest.main()
