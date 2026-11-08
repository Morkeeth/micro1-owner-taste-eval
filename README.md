# Can a frontier model predict one person's creative verdicts?

Video walkthrough: https://youtu.be/Wso5mTrxbIA

**TLDR.** We asked Opus 5.5 and GPT-6.1 to predict how one video creator (me) ruled on 65 real animation proposals: use it, edit it, needs new content, or kill it. On 34 decisions made *after* the test was locked, both models tied the dumbest baseline (always "use it": 16 of 34; Opus 16, GPT 17). Giving the models my 31 earlier verdicts and notes did not help. Point estimates fell (Opus 10, GPT 14). The models' reasons suggest they turned my past complaints into rules, and they over-predicted "kill". None of these differences is statistically reliable at this sample size. We claim no win for any system.

## What it tests

I run a phone review panel. Coding agents propose things (animations, cuts, posts) as cards, and I answer each card with one tap and sometimes a note. That gives a clean, timestamped record of one person's taste on real work.

The hackathon question: is this a task where frontier models fall short, and does a person's own decision history help close the gap?

## Why it matters

Agents that make things for a person need to know what that person will accept, or they keep asking. If a frontier model could predict one creator's verdicts, an agent could skip the review step. This test measures how far that is from true today, on real decisions with a pre-declared baseline, and whether the simplest form of personal memory helps.

## Data

All cases are animation proposals for my YouTube channel, offered with the same four answers: **AWESOME, USE IT / EDIT THIS ONE / NEEDS NEW CONTENT / KILL THIS ONE.**

| Study | Cases | Selection | When the owner decided |
|---|---|---|---|
| A, retrospective | 31 | every four-way decision in one fixed review window | before the study was assembled |
| B, prospective | 34 | every later four-way decision up to a fixed cutoff | **after** study A's protocol was frozen |

Each case gives the model what I saw: the exact card text as shown (snapshot pinned by hash) and the first still image on the card. My answer and note are kept in a separate label file and never sent to a model. One later decision was dropped because it offered different answers.

Study B is split before any model output into **fresh** cards (25) and **revision** cards (9). A revision card says it fixes a version I sent back, which is a strong hint that I will approve it.

## Method

Two routes through OpenRouter, provider-pinned: `anthropic/claude-opus-5.5` and `openai/gpt-6.1-sol`. Medium reasoning, 2048-token cap, strict JSON choice, no tools, no retries, no fallback.

Two arms in study B:

- **RAW**: the exact prompt frozen for study A. Card text plus still image.
- **HISTORY**: the same, plus all 31 study A decisions as text (card title, description, my choice, my note). No selection or tuning. This is the simplest version of "the model knows my taste".

Baseline: **always AWESOME**, fixed from study A's majority (17 of 31) before study B existed.

Uncertainty: Wilson intervals per arm, and a cluster bootstrap (10,000 resamples, seed 20261108) over groups of related clips, because several cards are versions of the same shot.

## Results

### Study B, primary endpoint (all 34 cases)

| Arm | Opus 5.5 | GPT-6.1 | Always AWESOME |
|---|---|---|---|
| RAW | 16 | 17 | 16 |
| HISTORY | 10 | 14 | 16 |

Model minus baseline, cluster 95% interval: RAW Opus -18 to +19 points, RAW GPT -14 to +23 points. **A tie.**

HISTORY minus RAW, cluster 95% interval: Opus -40 to +4 points, GPT -28 to +7 points. Exact McNemar p = 0.15 (Opus) and 0.45 (GPT). **The drop is not reliable at this sample size.**

### Study B, secondary (fresh cards only, 25)

RAW: Opus 12, GPT 12. Always AWESOME: 9. Always EDIT would also score 9, because fresh cards split 9 AWESOME and 9 EDIT. Both intervals include zero.

### Study A (31 cases, RAW only)

Opus 14, GPT 12, always AWESOME 17. Cluster intervals include zero. Study A was assembled after the outcomes were known, so it is weaker evidence than study B.

## Exploratory findings (post hoc, not pre-registered)

**1. History made the models harsher.** With my history attached, Opus guessed KILL 10 times and GPT 8 times. I actually chose KILL 3 times. The reasons show the mechanism. On a phone-notification shot I approved, RAW Opus said it was "exactly the kind of general notifications shot the owner asked for". HISTORY Opus said "the owner has rejected similar quiet, low-energy shots" and cited my note that a different clip was "slightly boring with the white panels". The model treated one-off complaints as standing rules. My notes are reactions to a specific clip, not a style guide.

**2. The proposing agent's recommendation explains a lot.** Most study B cards end with the agent's own recommendation ("Use it under any weekly limit talk", "Probably kill"). A keyword rule that just follows it scores 17 of 34, the same as GPT. GPT's RAW answer matched that rule on 30 of 34 cases. So on these cards, a good part of the RAW accuracy may be reading the proposer's own advice rather than judging the image. Study A cards mostly carried a neutral recommendation.

**3. Matching the button is not matching the reason.** On one study A clip I chose EDIT and wrote "Slight skew on the screen recording". Both models chose EDIT. Neither mentioned the skew. An agent that acts on the prediction would still fix the wrong thing.

## Limits

- One owner, 65 cases, related clips. Small samples and wide intervals throughout.
- Models saw one still. I watched the film with motion and sound.
- The agent that assembled study B saw my answers while assembling it, before writing the protocol. The RAW prompt was frozen earlier, so it could not be tuned on them. The HISTORY arm was written after the answers were visible, so it is disclosed as such. It uses all 31 history cases mechanically, with no selection.
- Some cards contain earlier feedback in their own text, and most study B cards contain the proposer's recommendation (see above).
- Venice was not run (no approved key in this lane). That is missing coverage, not a result.

## Cost

Study A: 62 calls, USD 0.4654. Study B: 136 calls, USD 1.9271. Both sums reconcile to the per-response costs reported by OpenRouter. Total USD 2.39.

## What we take from it

Frontier models are not clearly worse than a constant at guessing my verdicts, and not clearly better. Naive personal history, pasted into the prompt, did not help and may hurt, because models generalise a person's notes too aggressively. If a personal method is going to beat a frontier model on taste, it has to model *when* a complaint applies, not just *that* it was made. That is the next experiment, with a larger, sealed set.

## How to run

```
python3 verify.py
```

Checks that every file frozen before study B still has its frozen hash, that all 198 saved model responses were made after their study's freeze time, then re-scores both studies (`replay.py`). Change one byte of a frozen file and it fails.

Needs only Python 3 and its standard library. Re-scores both studies from the saved raw model responses. No network, no API key. `study-*/run_*.py` show the exact calls; the study B runner refuses to start without the owner's spend approval and will not overwrite saved responses.

Files: `study-a-retrospective-31/` and `study-b-prospective-34/` each hold the protocol, manifest, inputs, stills, raw responses, labels, scorer and scores. Study B also holds `SUPPLEMENT.json` (balanced accuracy, per-class recall, paired tests) and `RECOMMENDATION-CUE.json` (the post-hoc recommendation baseline).

Paper: `paper/paper.pdf` (charts in `paper/`).

License: code MIT, data and paper CC BY 4.0. See `LICENSE`.
