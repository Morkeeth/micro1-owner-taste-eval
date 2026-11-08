"""Repeat trials 2 and 3 of both frozen studies. Sequential, no retries, cap USD 6.

Refuses to run without Oscar's YES on micro1-repeat-trials-8nov.
Never writes into either study folder and never calls either study's runner.
Each request body is rebuilt and must hash to the SAME request_sha256 as the
saved trial 1 request, so trials 2 and 3 are the identical frozen request.
"""
import base64, decimal, hashlib, json, os, sys, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime

HERE = Path(__file__).resolve().parent
DAY = HERE.parent
A = DAY / "MICRO1-OWNER-WINDOW-FROZEN-e87f7594"
B = DAY / "MICRO1-PROSPECTIVE-28"
D = decimal.Decimal
CARD = "micro1-repeat-trials-8nov"
CAP = D("6")
TRIALS = [2, 3]
PRICE = {"anthropic": (D("0.000008"), D("0.00002")), "openai": (D("0.000005"), D("0.000015"))}
ROUTES = [
    {"pin": "anthropic", "model": "anthropic/claude-opus-5.5",
     "allowed": ["anthropic/claude-opus-5.5", "anthropic/claude-opus-5.5-20260921"],
     "max_price": {"prompt": 4, "completion": 20, "request": 0, "image": 0}},
    {"pin": "openai", "model": "openai/gpt-6.1-sol",
     "allowed": ["openai/gpt-6.1-sol", "openai/gpt-6.1-sol-20260929"],
     "max_price": {"prompt": 4, "completion": 15, "request": 0, "image": 0}},
]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
now = lambda: datetime.now().astimezone().isoformat()


def save(p, x):
    t = p.with_suffix(p.suffix + ".tmp")
    t.write_text(json.dumps(x, ensure_ascii=False, indent=2) + "\n")
    os.replace(t, p)


def authorized():
    for line in open(Path.home() / ".local/state/fleet/review-queue/verdicts.jsonl"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("id") == CARD and d.get("verdict", "") == "YES, BOTH STUDIES UP TO $6":
            return d
    return None


def body_for(model_text, img, route, options):
    mime = "image/png" if img.suffix == ".png" else "image/webp" if img.suffix == ".webp" else "image/jpeg"
    content = [{"type": "text", "text": model_text},
               {"type": "image_url", "image_url": {"url": "data:" + mime + ";base64," + base64.b64encode(img.read_bytes()).decode()}}]
    return {"model": route["model"], "messages": [{"role": "user", "content": content}], "max_tokens": 2048,
            "reasoning": {"effort": "medium"},
            "provider": {"only": [route["pin"]], "allow_fallbacks": False, "require_parameters": True, "max_price": route["max_price"]},
            "plugins": [], "transforms": [],
            "response_format": {"type": "json_schema", "json_schema": {"name": "owner_choice", "strict": True, "schema": {
                "type": "object", "properties": {"choice": {"type": "string", "enum": options}, "reason": {"type": "string"}},
                "required": ["choice", "reason"], "additionalProperties": False}}}}


def jobs():
    """Yield (study, case_id, arm, route, text, img, trial1_file) in run order."""
    pb = json.load(open(B / "PROTOCOL.json")); mb = json.load(open(B / "MANIFEST.json"))
    pa = json.load(open(A / "PROTOCOL.json")); ma = json.load(open(A / "MANIFEST.json"))
    fr = json.load(open(B / "FREEZE.json"))
    for f in ["PROTOCOL.json", "MANIFEST.json", "HISTORY-BLOCK.json"]:
        assert sha(B / f) == fr[f], f
    def case_text(inp):
        return "\n\nCASE\n" + json.dumps({"case_id": inp["case_id"], "card": inp["shown_card_text"],
                                          "visual_input_policy": inp["visual_input_policy"]}, ensure_ascii=False)
    for trial in TRIALS:
        for arm in ["RAW", "HISTORY"]:
            for case in mb:
                assert sha(case["input"]) == case["input_sha256"]
                inp = json.load(open(case["input"])); img = Path(inp["poster"]); assert sha(img) == inp["poster_sha256"]
                text = pb["arms"][arm]["prompt"] + case_text(inp)
                for r in ROUTES:
                    yield trial, "study-b", case["case_id"], arm, r, text, img, pb["options"], B / "responses" / f"{case['case_id']}-{arm}-{r['pin']}.json"
        for case in ma:
            assert sha(case["input"]) == case["input_sha256"]
            inp = json.load(open(case["input"])); img = Path(inp["poster"]); assert sha(img) == inp["poster_sha256"]
            text = pa["model_prompt"] + case_text(inp)
            for r in ROUTES:
                yield trial, "study-a", case["case_id"], "RAW", r, text, img, pa["options"], A / "responses" / f"{case['case_id']}-{r['pin']}.json"


def main():
    dry = "--dry" in sys.argv
    v = authorized(); assert v, "No Oscar YES, BOTH STUDIES verdict on " + CARD
    acct_p = HERE / "ACCOUNTING.json"
    if not dry:
        assert not acct_p.exists(), "accounting exists: no rerun"
        key = os.environ["OPENROUTER_API_KEY"]
    plan = list(jobs())
    # Pre-dispatch proof: every rebuilt request equals the saved trial 1 request.
    for trial, study, cid, arm, r, text, img, options, t1 in plan:
        body = body_for(text, img, r, options)
        rh = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        assert rh == json.load(open(t1))["request_sha256"], f"request differs from trial 1: {t1.name}"
    print(json.dumps({"planned_calls": len(plan), "all_requests_match_trial_1": True}))
    if dry:
        return
    lock = HERE / "RUN.lock"; lock.mkdir()
    acct = {"at": now(), "authority_verdict": v, "cap_usd": str(CAP), "spent_usd": "0", "reserved_usd": "0",
            "completed": 0, "planned": len(plan), "status": "RUNNING"}
    save(acct_p, acct)

    def stop(s, **k):
        acct.update(status=s, at=now(), **k); save(acct_p, acct); sys.exit(s)
    try:
        for trial, study, cid, arm, r, text, img, options, t1 in plan:
            outdir = HERE / "responses" / f"trial-{trial}" / study; outdir.mkdir(parents=True, exist_ok=True)
            out = outdir / t1.name; assert not out.exists()
            pin, pout = PRICE[r["pin"]]; reserve = (len(text.encode()) + 6000) * pin + 2048 * pout
            if D(acct["spent_usd"]) + reserve > CAP:
                stop("STOPPED_BEFORE_DISPATCH_BUDGET", next=str(out.relative_to(HERE)))
            body = body_for(text, img, r, options)
            rh = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
            acct.update(reserved_usd=str(reserve), current=str(out.relative_to(HERE)), at=now()); save(acct_p, acct)
            try:
                req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                             headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=180) as resp:
                    response = json.load(resp)
            except Exception as e:
                save(out, {"at": now(), "trial": trial, "study": study, "case_id": cid, "arm": arm, "route": r["pin"],
                           "request_sha256": rh, "error": type(e).__name__,
                           "body": e.read().decode(errors="replace") if isinstance(e, urllib.error.HTTPError) else str(e),
                           "charge_status": "UNKNOWN_FULL_RESERVE_RETAINED"})
                stop("STOPPED_AMBIGUOUS_REQUEST_NO_RETRY")
            cost = response.get("usage", {}).get("cost")
            save(out, {"at": now(), "trial": trial, "study": study, "case_id": cid, "arm": arm, "route": r["pin"],
                       "request_sha256": rh, "reserve_usd": str(reserve), "response": response, "actual_reported_cost_usd": cost})
            if cost is None or D(str(cost)) < 0:
                stop("STOPPED_UNKNOWN_BILLING_FULL_RESERVE_RETAINED")
            if D(str(cost)) > reserve:
                stop("STOPPED_COST_ABOVE_RESERVE", cost=str(cost))
            acct.update(spent_usd=str(D(acct["spent_usd"]) + D(str(cost))), reserved_usd="0", completed=acct["completed"] + 1, at=now())
            save(acct_p, acct)
            print(json.dumps({"call": str(out.relative_to(HERE)), "done": acct["completed"], "spent": acct["spent_usd"]}), flush=True)
            if response.get("error"):
                stop("STOPPED_PROVIDER_ERROR")
            if response.get("model") not in r["allowed"]:
                stop("STOPPED_MODEL_ID_MISMATCH", model=response.get("model"))
        acct.update(status="COMPLETED", reserved_usd="0", at=now()); save(acct_p, acct)
    finally:
        lock.rmdir()


if __name__ == "__main__":
    main()
