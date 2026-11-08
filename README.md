# Can a frontier model predict one person's creative verdicts?

Video walkthrough: https://youtu.be/4x3BjuDlWQU

**Two frontier models could not reliably beat a bot that always says yes at predicting my real creative decisions. Giving them my own past verdicts made them stricter, not better.**

- 65 real decisions from my own review panel, in two studies. The protocol was frozen before any model call. The second study uses only decisions I made after the freeze.
- In the headline run, Opus 5.5 and GPT-6.1 matched 16 and 17 of 34. Always saying yes matched 16. With my history attached they fell to 10 and 14.
- Three trials per task with byte-identical requests: GPT scored 17, 18 and 18; Opus 16, 17 and 13. With my history, Opus guessed KILL 10, 11 and 11 times and GPT 8, 8 and 8 times. The harsher-with-history pattern repeated in every trial.
- Why they fail: they turn one-off complaints into rules. Opus killed a shot I approved because I once called a different clip's white panels boring.
- Every raw response is kept, and every number replays offline with no API key. Total model cost for this entry: USD 6.67. Small samples: no score gap is statistically reliable.

## Why it matters

More and more creative work is made by agents and approved by one person: a video editor, a designer, a founder. Each approval costs that person time. The promise of personal AI is that a model learns what this person will accept, and the agent stops asking.

This eval measures how far that promise is from true today. It uses the exact cards a real person approved or rejected, with the exact still they saw, and a baseline fixed in advance. If a frontier model cannot beat "always say yes" on one person's real decisions, an agent that relies on it to skip review will ship work the person would have killed, and kill work they would have kept. The second failure is worse, and it is the one personal history made more common here.

## What it tests

Each task is one real review card from my panel: an animation proposal for my YouTube channel, offered with four answers: **AWESOME, USE IT / EDIT THIS ONE / NEEDS NEW CONTENT / KILL THIS ONE.** The model sees what I saw: the exact card text as shown (snapshot pinned by hash) and the first still on the card. It must answer with one of the four options in strict JSON.

**Reference answer.** My own recorded verdict, saved with a timestamp at the moment I tapped it, before any model existed for this test. No model ever saw a label. The usual "would two experts agree?" test does not fit a taste task: the question is what *this* person decided, and that is a recorded fact. So the reference cannot be argued with, and it cannot be tuned after the fact.

| Study | Cases | Selection | When I decided |
|---|---|---|---|
| A, retrospective | 31 | every four-way decision in one fixed review window | before the study was assembled |
| B, prospective | 34 | every later four-way decision up to a fixed cutoff | **after** study A's protocol was frozen |

Study B is split before any model output into **fresh** cards (25) and **revision** cards (9). A revision card says it fixes a version I sent back, which is a strong hint that I will approve it. One later decision was dropped because it offered different answers.

## Method

- Routes through OpenRouter, provider-pinned: `anthropic/claude-opus-5.5` and `openai/gpt-6.1-sol`. Medium reasoning, 2048-token cap, strict JSON schema, no tools, no retries, no fallback. Each served model id is checked against an allow-list.
- **RAW** arm: the exact prompt frozen for study A. Card text plus still image.
- **HISTORY** arm (study B): the same, plus all 31 study A decisions as text (card title, description, my choice, my note). No selection or tuning. This is the simplest version of "the model knows my taste".
- **Baseline:** always AWESOME, fixed from study A's majority (17 of 31) before study B existed.
- **Trials:** three per task. Trial 1 is the frozen run and the headline. Trials 2 and 3 send byte-identical requests (each request hash is checked against trial 1 before dispatch) and are reported as spread, majority vote and pass^3. The headline rule, spread and majority-vote reporting were set before trials 2 and 3 ran; pass^3 and the stability count follow the judging guide's standard summaries.
- **Uncertainty:** Wilson intervals per arm, and a cluster bootstrap (10,000 resamples, seed 20261108) over groups of related clips, because several cards are versions of the same shot.
- **Run dates:** study A trial 1 on 8 Nov 2026, 03:31 to 03:35 Paris. Study B trial 1 on 8 Nov 2026, 12:57 to 13:07. Trials 2 and 3 on 8 Nov 2026, 19:21 to 19:50 Paris.

## Grader

Exact match on one of four labels, from strict JSON. No LLM judge. The self-test runs the real scorers on synthetic answers in a temporary copy:

```
== study-a-retrospective-31
  PASS  reference  anthropic 31/31, openai 31/31
  PASS  wrong      anthropic 0/31, openai 0/31
  PASS  malformed  scorer refused to score (fails loud)
  PASS  gaming     anthropic 0/31, openai 0/31
  PASS  truncated  anthropic 0/31, openai 0/31
== study-b-prospective-34
  PASS  reference  RAW-anthropic 34/34, RAW-openai 34/34, HISTORY-anthropic 34/34, HISTORY-openai 34/34
  PASS  wrong      RAW-anthropic 0/34, RAW-openai 0/34, HISTORY-anthropic 0/34, HISTORY-openai 0/34
  PASS  malformed  RAW-anthropic 0/34, RAW-openai 0/34, HISTORY-anthropic 0/34, HISTORY-openai 0/34
  PASS  gaming     RAW-anthropic 0/34, RAW-openai 0/34, HISTORY-anthropic 0/34, HISTORY-openai 0/34
  GAP   truncated  frozen scorer would accept a cut-off reply; saved replies cut off: 0 of 136, so scores are unaffected
ALL GRADER CHECKS PASS
```

The one gap: study B's scorer is hash-frozen and does not read `finish_reason`, so a cut-off reply with the right label would count. I left it frozen rather than edit a frozen file, and the self-test proves no saved study B reply was cut off. The trial scorer (`trials/score_trials.py`) does check it.

## Results

### Study B, primary endpoint (34 decisions made after the freeze)

| Arm | Opus 5.5 | GPT-6.1 | Always AWESOME |
|---|---|---|---|
| RAW, trial 1 (headline) | 16 | 17 | 16 |
| HISTORY, trial 1 | 10 | 14 | 16 |
| RAW, trials 2 and 3 | 17, 13 | 18, 18 | 16 |
| HISTORY, trials 2 and 3 | 12, 10 | 15, 14 | 16 |
| RAW, majority of 3 | 16 | 17 | 16 |
| HISTORY, majority of 3 | 12 | 14 | 16 |

Trial 1, model minus baseline, cluster 95% interval: RAW Opus -18 to +19 points, RAW GPT -14 to +23 points. **A tie.** HISTORY minus RAW: Opus -40 to +4 points, GPT -28 to +7 points; exact McNemar p = 0.15 (Opus) and 0.45 (GPT). **Not reliable at this sample size.**

Fresh cards only (25), trial 1: RAW Opus 12, GPT 12, always AWESOME 9. Always EDIT would also score 9, because fresh cards split 9 AWESOME and 9 EDIT. Both intervals include zero.

### Study A (31 decisions, RAW)

| Trial | Opus 5.5 | GPT-6.1 | Always AWESOME |
|---|---|---|---|
| Trial 1 (headline) | 14 | 12 | 17 |
| Trials 2 and 3 | 11, 9 | 14, 13 | 17 |
| Majority of 3 | 11 | 13 | 17 |

Trial 1 cluster intervals include zero. Study A was assembled after the outcomes were known, so it is weaker evidence than study B.

### Across three trials

Always AWESOME beat every model in every study A trial. In study B no model was ever more than two cards ahead of it, inside the trial 1 interval. Adding my history lowered the score in every trial for both models, and the KILL guesses held steady: Opus 10, 11 and 11, GPT 8, 8 and 8, against my 3. GPT is consistent (same answer all three times on 31 of 34 RAW cases); Opus is not (25 of 34). Right on all three trials (pass^3), study B RAW: Opus 12 of 34, GPT 17 of 34. Full table: `trials/TRIALS-SCORES.json`.

## Why the models fail

Verbatim replies for five failures are in `transcripts/TRANSCRIPTS.md`. Three patterns, all post hoc:

**1. History made the models harsher.** With my history attached, Opus guessed KILL 10 times and GPT 8 times in trial 1. I chose KILL 3 times. Without history they guessed KILL 3 and 2 times. On a phone-notification shot I approved, RAW Opus said it was "exactly the kind of general notifications shot the owner asked for". HISTORY Opus said "the owner has rejected similar quiet, low-energy shots" and cited my note that a different clip was "slightly boring with the white panels". The model treated a one-off complaint as a standing rule.

**2. The proposing agent's recommendation explains a lot.** Most study B cards end with the proposing agent's own advice ("Use it under any weekly limit talk", "Probably kill"). A keyword rule that just follows it scores 17 of 34, the same as GPT. GPT's RAW answer matched that rule on 30 of 34 cases. A good part of the RAW accuracy may be reading the proposer's advice rather than judging the work.

**3. Matching the button is not matching the reason.** On one study A clip I chose EDIT and wrote "Slight skew on the screen recording". Both models chose EDIT. Neither mentioned the skew. An agent that acts on the prediction would still fix the wrong thing.

## Limits

- One person, 65 decisions, related clips. Small samples and wide intervals throughout.
- Models saw one still. I watched the clip with motion and sound.
- The agent that assembled study B saw my answers while assembling it, before writing the protocol. The RAW prompt was frozen earlier, so it could not be tuned on them. The HISTORY arm was written after the answers were visible. It uses all 31 history cases mechanically, with no selection.
- Some cards contain earlier feedback in their own text, and most study B cards contain the proposer's recommendation (see above).
- Venice was not run (no approved key). That is missing coverage, not a result.

## How to run

Needs only Python 3 and its standard library (tested on 3.12.5 and 3.9.6). From the folder that holds this README:

```
python3 verify.py            # audit: frozen files unchanged, every response made after its freeze, then replay
python3 replay.py            # re-score both studies from saved responses, trial 1 (seconds)
python3 grader_selftest.py   # prove the grader accepts the reference and rejects wrong answers (about 15 seconds)
python3 trials/score_trials.py   # score all three trials (seconds)
python3 make_transcripts.py  # rebuild transcripts/TRANSCRIPTS.md from saved responses
python3 study-b-prospective-34/score_supplement.py           # balanced accuracy, recall, McNemar p
python3 study-b-prospective-34/score_recommendation_cue.py   # the post-hoc recommendation baseline
```

No network, no API key. To re-run the models yourself, copy `.env.example`, set `OPENROUTER_API_KEY`, and use `study-*/run_*.py` or `trials/run_trials.py`. Each runner refuses to overwrite saved responses, and the study B and trials runners also refuse to start without my recorded spend approval. A live rerun therefore needs an empty output folder, and for those two runners an edit you make on purpose. A full live run of all three trials is 594 calls and takes about an hour.

Folders: `study-a-retrospective-31/` and `study-b-prospective-34/` each hold the protocol, manifest, inputs, stills, raw responses, labels, scorer and scores. Study B also holds `SUPPLEMENT.json` (balanced accuracy, per-class recall, paired tests) and `RECOMMENDATION-CUE.json` (the post-hoc recommendation baseline). `trials/` holds the repeat runs, their accounting and `TRIALS-SCORES.json`.

## Cost

Per-response costs reported by OpenRouter; each sum reconciles to the saved responses. This is not an invoice.

| Run | Calls | USD |
|---|---|---|
| Study A, trial 1 | 62 | 0.4654 |
| Study B, trial 1 | 136 | 1.9271 |
| Trials 2 and 3, both studies | 396 | 4.2781 |
| **This entry** | 594 | **6.67** |

Before these studies, a 1 Nov exploratory benchmark on 30 different review cards (Opus, GPT, Gemini and Jev) cost USD 2.51. It shaped the design but is not part of this entry's data.

## How AI tools were used

- **Mine:** every label. Each is my own one-tap verdict on a real card in my review panel, made while working, and timestamped. I chose the question, approved each paid run in the panel before it ran, reviewed the results, and approved the write-up and paper.
- **Coding agents:** built the harness, froze the protocol, ran the calls, wrote the scorers and the self-test, and drafted this README.
- **How it was checked:** the frozen hashes, the grader self-test, the offline replay, and reading the transcripts. I did not hand-check every line of scorer code; the self-test is that check.

## What we take from it

Frontier models are not clearly worse than a constant at guessing my verdicts, and not clearly better. Naive personal history, pasted into the prompt, did not help and pushed both models toward rejecting work, because they generalise a person's notes too aggressively. Taste is knowing when a complaint applies. A personal method that beats a frontier model has to model that, and that is the next experiment, on a larger sealed set.

## Repository extras

`verify.py` checks that every file frozen before study B still has its frozen hash, that all saved study A and B responses were made after their study's freeze time, then runs `replay.py`. Change one byte of a frozen file and it fails.

Paper: `paper/paper.pdf` (charts in `paper/`).

License: code MIT, data and paper CC BY 4.0. See `LICENSE`.
