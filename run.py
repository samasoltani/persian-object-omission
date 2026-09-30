# -*- coding: utf-8 -*-
"""
run.py - run one numbered step, save its output, and push everything to GitHub
===============================================================================
Usage (in the PyCharm terminal, from the project root):

    python run.py 05

It will:
  1. find the script whose name starts with "05-"
  2. run it with the same Python interpreter (the project's .venv)
  3. show the output AND save it to outputs/logs/05_log.txt (UTF-8)
  4. git add -A, commit ("Run 05-..."), pull --rebase, push

Then just tell Claude "05 done" - the log is read from GitHub.
"""

import os
import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 2:
    sys.exit("Usage: python run.py <step number>, e.g.  python run.py 05")

step = sys.argv[1].zfill(2)
matches = sorted(Path(".").glob(f"{step}-*.py"))
if not matches:
    sys.exit(f"No script starting with '{step}-' in {Path('.').resolve()}")
script = matches[0]

log_dir = Path("outputs/logs")
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"{step}_log.txt"

env = dict(os.environ, PYTHONIOENCODING="utf-8")
print(f"=== Running {script.name} ===\n")
proc = subprocess.run([sys.executable, str(script)], capture_output=True,
                      text=True, encoding="utf-8", errors="replace", env=env)
output = proc.stdout + (("\n=== STDERR ===\n" + proc.stderr) if proc.stderr else "")
output += f"\n=== exit code: {proc.returncode} ===\n"
print(output)
log_file.write_text(output, encoding="utf-8")
print(f"Log saved to {log_file}")


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    msg = (r.stdout + r.stderr).strip()
    if msg:
        print(f"[git {args[0]}] {msg}")
    return r.returncode


print("\n=== Pushing to GitHub ===")
git("add", "-A")
git("commit", "-m", f"Run {script.stem}")
if git("pull", "--rebase") != 0:
    sys.exit("git pull --rebase failed - send the message above to Claude.")
if git("push") != 0:
    sys.exit("git push failed - send the message above to Claude.")
print("\nDone. Tell Claude:", f"{step} done")
