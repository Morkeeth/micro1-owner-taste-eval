"""Grader self-test. Runs the REAL scorers of both studies on synthetic answers in a temporary copy.

Checks, per study:
  1. reference:  answering with my recorded verdict on every case scores n/n
  2. wrong:      answering with any other valid option on every case scores 0/n
  3. malformed:  non-JSON content never scores: study B counts it invalid,
                 study A refuses to produce scores at all (fails loud)
  4. gaming:     one answer naming all four options scores 0/n
  5. truncated:  the right label in a cut-off (finish_reason=length) reply scores 0/n.
                 Known gap: study B's scorer is hash-frozen and does not read finish_reason,
                 so instead this checks that none of the saved study B replies were cut off.

No network, no API key. The saved model responses are never modified.
Usage: python3 grader_selftest.py
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

R = Path(__file__).resolve().parent
OPTIONS = ["AWESOME, USE IT", "EDIT THIS ONE", "NEEDS NEW CONTENT", "KILL THIS ONE"]


def labels(study_dir):
    raw = json.loads((study_dir / "labels/owner-verdicts.json").read_text())
    out = {}
    for row in raw:
        out[row["case_id"]] = row.get("verdict") or row.get("label_exact")
    return out


def rewrite(tmp, truth, make):
    """make(case_id, truth_label) -> (content_string, finish_reason)"""
    for f in sorted((tmp / "responses").glob("*.json")):
        cid = f.name.split("-")[0]
        data = json.loads(f.read_text())
        content, finish = make(cid, truth[cid])
        choice = data["response"]["choices"][0]
        choice["message"]["content"] = content
        choice["finish_reason"] = finish
        f.write_text(json.dumps(data))


def score(tmp, script):
    out = subprocess.run([sys.executable, "-I", str(tmp / script)], capture_output=True, text=True, cwd=tmp)
    if out.returncode:
        return out.stderr
    return json.loads((tmp / "SCORES.json").read_text())


def counts(res):
    """Return {arm: (correct, n, invalid)} for either scorer's output shape."""
    if "routes" in res:  # study A
        return {k: (v["correct"], v["n"], v["invalid_or_missing"]) for k, v in res["routes"].items() if "correct" in v}
    a = res["all"]
    return {k: (a[k]["correct"], a["n"], a[k]["invalid"]) for k in a if isinstance(a.get(k), dict) and "correct" in a[k]}


def answer(label):
    return json.dumps({"choice": label, "reason": "self-test"})


CASES = [
    ("reference", lambda cid, t: (answer(t), "stop"), "all"),
    ("wrong", lambda cid, t: (answer(next(o for o in OPTIONS if o != t)), "stop"), "none"),
    ("malformed", lambda cid, t: ("I think " + t, "stop"), "none"),
    ("gaming", lambda cid, t: (answer(" / ".join(OPTIONS)), "stop"), "none"),
    ("truncated", lambda cid, t: (answer(t), "length"), "none"),
]

STUDIES = [("study-a-retrospective-31", "score_frozen.py"), ("study-b-prospective-34", "score_prospective.py")]


def main():
    failures = 0
    for study, script in STUDIES:
        src = R / study
        truth = labels(src)
        print(f"== {study}")
        for name, make, expect in CASES:
            with tempfile.TemporaryDirectory() as td:
                tmp = Path(td) / study
                shutil.copytree(src, tmp)
                rewrite(tmp, truth, make)
                res = score(tmp, script)
            if isinstance(res, str):
                # Study A stops instead of scoring when a reply cannot be parsed:
                # its cost no longer reconciles. Refusing to score is a pass for
                # the malformed check only; any other crash is a failure.
                ok = name == "malformed" and "accounting_reconciled" in res
                failures += not ok
                print(f"  {'PASS' if ok else 'FAIL'}  {name:<10} scorer refused to score (fails loud)")
                if not ok:
                    print(res)
                continue
            got = counts(res)
            ok = all((c == n) if expect == "all" else (c == 0) for c, n, _ in got.values())
            if name == "malformed":
                ok = ok and all(inv == n for _, n, inv in got.values())
            if not ok and name == "truncated" and study.startswith("study-b"):
                # Known gap: the hash-frozen study B scorer does not read finish_reason.
                # We leave it frozen and instead prove no saved reply is affected.
                cut = [f.name for f in sorted((src / "responses").glob("*.json"))
                       if json.loads(f.read_text())["response"]["choices"][0].get("finish_reason") != "stop"]
                ok = not cut
                print(f"  {'GAP ' if ok else 'FAIL'}  {name:<10} frozen scorer would accept a cut-off reply; "
                      f"saved replies cut off: {len(cut)} of {len(list((src / 'responses').glob('*.json')))}, so scores are unaffected")
                failures += not ok
                continue
            failures += not ok
            detail = ", ".join(f"{k} {c}/{n}" for k, (c, n, _) in got.items())
            print(f"  {'PASS' if ok else 'FAIL'}  {name:<10} {detail}")
    print("ALL GRADER CHECKS PASS" if not failures else f"{failures} GRADER CHECK(S) FAILED")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
