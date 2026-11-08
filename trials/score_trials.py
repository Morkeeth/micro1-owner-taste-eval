"""Score all three trials of both studies. Trial 1 is the frozen headline; trials 2 and 3 are the
pre-declared repeat runs, reported as spread, majority vote, pass^3 and answer stability.
No network. Writes TRIALS-SCORES.json next to this file.
"""
import json, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
if (HERE.parent / "study-b-prospective-34").exists():      # inside the package
    A, B = HERE.parent / "study-a-retrospective-31", HERE.parent / "study-b-prospective-34"
else:                                                         # working folder
    A, B = HERE.parent / "MICRO1-OWNER-WINDOW-FROZEN-e87f7594", HERE.parent / "MICRO1-PROSPECTIVE-28"
OPTIONS = ["AWESOME, USE IT", "EDIT THIS ONE", "NEEDS NEW CONTENT", "KILL THIS ONE"]


def choice(path):
    """Valid choice string, or None for missing, cut-off, malformed or off-menu replies."""
    if not path.exists():
        return None
    try:
        d = json.loads(path.read_text())
        c = d["response"]["choices"][0]
        if c.get("finish_reason") != "stop":
            return None
        ch = json.loads(c["message"]["content"]).get("choice")
        return ch if ch in OPTIONS else None
    except Exception:
        return None


def arms():
    la = {l["case_id"]: l["label_exact"] for l in json.loads((A / "labels/owner-verdicts.json").read_text())}
    lb = {l["case_id"]: l["verdict"] for l in json.loads((B / "labels/owner-verdicts.json").read_text())}
    for pin in ["anthropic", "openai"]:
        yield "study-a", "RAW", pin, la, lambda cid, t, pin=pin: (A / "responses" / f"{cid}-{pin}.json") if t == 1 else HERE / "responses" / f"trial-{t}" / "study-a" / f"{cid}-{pin}.json"
    for arm in ["RAW", "HISTORY"]:
        for pin in ["anthropic", "openai"]:
            yield "study-b", arm, pin, lb, lambda cid, t, arm=arm, pin=pin: (B / "responses" / f"{cid}-{arm}-{pin}.json") if t == 1 else HERE / "responses" / f"trial-{t}" / "study-b" / f"{cid}-{arm}-{pin}.json"


def main():
    out = {}
    for study, arm, pin, lab, path in arms():
        ids = sorted(lab)
        picks = {cid: [choice(path(cid, t)) for t in (1, 2, 3)] for cid in ids}
        per_trial = [sum(picks[c][t] == lab[c] for c in ids) for t in range(3)]
        complete = all(None not in v for v in picks.values())
        maj = {}
        for c, v in picks.items():
            cnt = collections.Counter(x for x in v if x)
            top = cnt.most_common(1)
            maj[c] = top[0][0] if top and top[0][1] >= 2 else None
        out[f"{study} {arm} {pin}"] = {
            "n": len(ids),
            "correct_per_trial": per_trial,
            "all_trials_present_and_valid": complete,
            "majority_vote_correct": sum(maj[c] == lab[c] for c in ids),
            "pass_all_3": sum(all(x == lab[c] for x in picks[c]) for c in ids),
            "pass_any_3": sum(any(x == lab[c] for x in picks[c]) for c in ids),
            "same_answer_all_3": sum(len(set(picks[c])) == 1 and picks[c][0] is not None for c in ids),
            "kill_guesses_per_trial": [sum(picks[c][t] == "KILL THIS ONE" for c in ids) for t in range(3)],
        }
        if study == "study-a":
            out[f"{study} constant AWESOME"] = sum(lab[c] == "AWESOME, USE IT" for c in ids)
        else:
            out[f"{study} constant AWESOME"] = sum(lab[c] == "AWESOME, USE IT" for c in ids)
    (HERE / "TRIALS-SCORES.json").write_text(json.dumps(out, indent=1) + "\n")
    for k, v in out.items():
        if isinstance(v, dict):
            print(f"{k:<28} trials {v['correct_per_trial']}  majority {v['majority_vote_correct']}/{v['n']}  "
                  f"pass^3 {v['pass_all_3']}  stable {v['same_answer_all_3']}/{v['n']}  kills {v['kill_guesses_per_trial']}"
                  + ("" if v["all_trials_present_and_valid"] else "  (INCOMPLETE)"))
        else:
            print(f"{k:<28} {v}")


if __name__ == "__main__":
    main()
