# intent.md: what we set out to do (written before building)

## The customer's problem, in my own words

A team of 4 to 6 people meets in Korean and English around one shared AI speaker. Today the speaker costs them
meeting time instead of saving it: it jumps in whenever there is a pause, starts talking while someone is
mid-sentence, and keeps going after people tell it to stop. The team will only accept it if, in a real meeting,
it **stays quiet until someone calls it by name**, **never talks over a person**, and **stops at once when told**.

## Track and why

**Voice AI track.** The three acceptance conditions are decisions about *when to speak*, and that can be measured
from audio alone, without hardware or a user study. Open models already exist for the hard parts (wake word,
voice activity, keyword recognition). The missing piece is the logic that combines them, plus a fair
before/after measurement.

## Acceptance test (numbers, fixed before building)

Measured by `python -m quietgate.cli eval` on synthetic meeting scenes (seed 42), test split only.

| Metric | Pass if | Definition |
|---|---|---|
| Uncalled interruptions per 10 min | ≤ 0.5 | assistant starts with no wake call ending in the previous 8 s |
| Talk-over starts | 0 | assistant starts while a human is speaking (ground truth) |
| Missed calls | ≤ 10 % | wake calls with no assistant start within 3 s of the caller finishing |
| Stop latency, p95 | ≤ 0.5 s | end of the stop word → assistant audio stops |
| Stop misses | ≤ 5 % | assistant keeps talking > 1.5 s after a stop word |
| Reply delay after call, median | ≤ 1.5 s | guard metric, so the gate cannot "win" by never speaking |

**Before** = a typical naive assistant: it answers after any 700 ms pause and ignores "stop". Both use the same
detectors and the same evaluator.

## What I left out to fit 4 hours

- The assistant's brain (LLM, real answers): the reply is a fixed clip.
- Share of seats heard correctly (hardware track). Seat distance is only imitated with per-speaker gain (0 to -12 dB).
- Acoustic echo cancellation: the eval does not feed the reply back into the mic. The live demo uses headphones.
- Training a custom wake word: we reuse the pre-trained "hey_jarvis" model.
- A learned turn detector: we use a fixed 700 ms silence rule.
- Real recordings or the AMI corpus: synthetic voices only (no consent issues, fully reproducible).
