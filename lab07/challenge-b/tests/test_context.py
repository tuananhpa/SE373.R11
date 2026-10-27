import json
import tempfile
import unittest
from pathlib import Path
from compaction import make_history, compact, offline_continue, evaluate
from logs import generate_logs, Tools, EXPECTED
from code_runtime import run_code
from demo import run_b1, run_b2

SCRIPT = """import glob, re, collections
codes = collections.Counter()
for path in glob.glob("logs/*.log"):
    for line in open(path):
        m = re.search(r" ERROR \\S+ (ERR_[A-Z0-9_]+)\\b", line)
        if m:
            codes[m.group(1)] += 1
for code, n in codes.most_common(3):
    print(code, n)
"""

class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_checkpoint_retains_task_not_raw_log(self):
        history = make_history()
        checkpoint = compact(history)
        self.assertTrue(evaluate(offline_continue(checkpoint)))
        self.assertNotIn("RAW_LOG_MARKER", json.dumps(checkpoint))
        self.assertLess(len(json.dumps(checkpoint)), len(json.dumps(history)) // 20)
        self.assertFalse(evaluate(offline_continue(history[-1:])))

    def test_updated_next_action_wins(self):
        history = make_history()
        history.append({"kind":"next_action","value":"inspect transaction lock"})
        self.assertEqual(compact(history)["next_action"], "inspect transaction lock")

    def test_logs_and_script_agree_and_read_all_files(self):
        generate_logs(self.root)
        tools = Tools(self.root)
        self.assertEqual(len(tools.list_files()), 6)
        output, trace = run_code(SCRIPT, self.root)
        self.assertEqual(output.splitlines(), [f"{r['code']} {r['count']}" for r in EXPECTED])
        self.assertEqual(len([e for e in trace if e["tool"] == "read_file"]), 6)
        self.assertNotIn("RAW_LOG_MARKER", output)

    def test_script_can_close_its_file(self):
        generate_logs(self.root)
        code = SCRIPT.replace("for line in open(path):", "stream = open(path)\n    for line in stream:")
        code = code.replace("for code, n in codes.most_common(3):", "    stream.close()\nfor code, n in codes.most_common(3):")
        output, trace = run_code(code, self.root)
        self.assertEqual(output.splitlines(), [f"{r['code']} {r['count']}" for r in EXPECTED])

    def test_path_escape_is_rejected(self):
        generate_logs(self.root)
        for name in ("../secret", "/etc/passwd", "logs/../../secret", "logs/not-there.log"):
            with self.assertRaises((ValueError, FileNotFoundError)):
                Tools(self.root).read_file(name)

    def test_code_blocks_imports_dunder_and_unbounded_output(self):
        generate_logs(self.root)
        for code in ("import os", "print((1).__class__)", "while True: pass",
                     "print(open('../secret').read())", "print('x' * 20000)"):
            with self.assertRaises((ValueError, RuntimeError)):
                run_code(code, self.root)

    def test_code_timeout(self):
        generate_logs(self.root)
        with self.assertRaises(RuntimeError):
            run_code("for i in range(1000000000):\n    x = i * i", self.root, timeout=0.1)

    def test_offline_evidence_is_honest_and_results_correct(self):
        b1 = run_b1(self.root / "b1", live=False)
        self.assertTrue(b1["after"]["correct"])
        self.assertFalse(b1["truncated"]["correct"])
        self.assertIsNone(b1["after"]["usage"])
        b2 = run_b2(self.root / "b2", live=False)
        self.assertEqual(b2["raw"]["answer"]["errors"], EXPECTED)
        self.assertEqual(b2["code"]["answer"]["errors"], EXPECTED)
        self.assertGreater(b2["raw"]["context_chars"], b2["code"]["context_chars"])
        self.assertFalse(b2["llm_executed"])
        self.assertIsNone(b2["input_token_saving_percent"])

if __name__ == "__main__":
    unittest.main()
