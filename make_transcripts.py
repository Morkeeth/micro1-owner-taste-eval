"""Write transcripts/TRANSCRIPTS.md: verbatim model replies for five failure cases, read from the saved responses.
Usage (from the package root): python3 make_transcripts.py
"""
import json
from pathlib import Path

R = Path(__file__).resolve().parent
A = R / "study-a-retrospective-31"
B = R / "study-b-prospective-34"

CASES = [
    ("A", "C027", "I approved it after watching the clip; both models judged one blurry first frame and asked for edits."),
    ("A", "C004", "Both models picked my button, for a reason I never gave."),
    ("B", "P012", "My history turned one old complaint into a rule and flipped an approval into a kill."),
    ("B", "P013", "Same pattern in GPT: history made it reject a shot I approved."),
    ("B", "P026", "With history, GPT matched a new shot to a rejected old one and over-corrected to kill."),
]


def reply(path):
    d = json.loads(path.read_text())
    c = json.loads(d["response"]["choices"][0]["message"]["content"])
    return c["choice"], c["reason"], d["response"].get("model")


def main():
    la = {l["case_id"]: l for l in json.loads((A / "labels/owner-verdicts.json").read_text())}
    lb = {l["case_id"]: l for l in json.loads((B / "labels/owner-verdicts.json").read_text())}
    out = ["# Transcripts: five failures, verbatim", "",
           "Model text is copied unchanged from the saved responses (trial 1). My verdict and note come from the label file, which no model saw.", ""]
    for study, cid, lesson in CASES:
        if study == "A":
            card = json.loads((A / "inputs" / f"{cid}.json").read_text())["shown_card_text"]
            lab = la[cid]; verdict = lab["label_exact"]
            note = " ".join(e.get("note", "") for e in lab["canonical_events"]).strip()
            runs = [(f"{pin}", A / "responses" / f"{cid}-{pin}.json") for pin in ["anthropic", "openai"]]
        else:
            card = json.loads((B / "inputs" / f"{cid}.json").read_text())["shown_card_text"]
            lab = lb[cid]; verdict = lab["verdict"]; note = lab.get("note", "")
            runs = [(f"{arm} {pin}", B / "responses" / f"{cid}-{arm}-{pin}.json") for arm in ["RAW", "HISTORY"] for pin in ["anthropic", "openai"]]
        out += [f"## Study {study}, {cid}: {card['title']}", "", f"Why it is here: {lesson}", "",
                f"My verdict: **{verdict}**" + (f". My note: \"{note}\"" if note else ". No note."), ""]
        for label, path in runs:
            choice, reason, model = reply(path)
            mark = "match" if choice == verdict else "miss"
            out += [f"- **{label}** ({model}) chose **{choice}** ({mark}):", f"  \"{reason}\"", ""]
    (R / "transcripts").mkdir(exist_ok=True)
    (R / "transcripts" / "TRANSCRIPTS.md").write_text("\n".join(out) + "\n")
    print("wrote transcripts/TRANSCRIPTS.md")


if __name__ == "__main__":
    main()
