"""Run both independent test suites and portable evidence checks; no model calls."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
commands = [
    ("challenge-a",["-m","unittest","discover","-s","tests","-v"]),
    ("challenge-b",["-m","unittest","discover","-s","tests","-v"]),
    ("challenge-a",["demo.py","--verify","evidence/live-validation"]),
    ("challenge-b",["verify.py","evidence/live-validation"]),
    ("challenge-a",["demo.py","--verify","evidence/router-validation"]),
    ("challenge-b",["verify.py","evidence/router-validation-v2"]),
]
failed = False
for folder,args in commands:
    print("\n" + folder + " / " + " ".join(args),flush=True)
    result = subprocess.run([sys.executable,"-X","utf8","-B",*args],cwd=root/folder)
    failed = failed or result.returncode != 0
sys.exit(1 if failed else 0)
