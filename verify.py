#!/usr/bin/env python3
"""One-command audit: checks the pre-registration, then re-scores both studies.

1. Every file named in study B's FREEZE.json still has the hash it had when frozen.
2. Every saved model response in study B was made after the freeze time.
3. Every saved response in study A was made after study A's protocol was frozen.
4. Re-scores both studies from the saved raw responses (replay.py).

Python 3 standard library only. No network, no API key.
"""
import glob
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(ROOT, "study-a-retrospective-31")
B = os.path.join(ROOT, "study-b-prospective-34")
failures = 0


def check(ok, msg):
    global failures
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok:
        failures += 1


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def response_times(study):
    times = []
    for p in sorted(glob.glob(os.path.join(study, "responses", "*.json"))):
        with open(p) as f:
            times.append(datetime.fromisoformat(json.load(f)["at"]))
    return times


freeze = json.load(open(os.path.join(B, "FREEZE.json")))
frozen_b = datetime.fromisoformat(freeze["frozen_at"])
for name, digest in freeze.items():
    if name in ("frozen_at", "note"):
        continue
    check(sha(os.path.join(B, name)) == digest, f"study B frozen file unchanged: {name}")

tb = response_times(B)
check(len(tb) == 136 and min(tb) > frozen_b,
      f"study B: {len(tb)} responses, first at {min(tb).isoformat(timespec='seconds')}, "
      f"all after freeze {frozen_b.isoformat(timespec='seconds')}")

frozen_a = datetime.fromisoformat(json.load(open(os.path.join(A, "PROTOCOL.json")))["frozen_at"])
ta = response_times(A)
check(len(ta) == 62 and min(ta) > frozen_a,
      f"study A: {len(ta)} responses, first at {min(ta).isoformat(timespec='seconds')}, "
      f"all after protocol freeze {frozen_a.isoformat(timespec='seconds')}")

print()
r = subprocess.run([sys.executable, os.path.join(ROOT, "replay.py")], cwd=ROOT)
check(r.returncode == 0, "replay.py re-scored both studies")

print()
print("ALL CHECKS PASSED" if failures == 0 else f"{failures} CHECK(S) FAILED")
sys.exit(1 if failures else 0)
