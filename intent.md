# intent.md: the problem, the acceptance test and the scope

> The acceptance test below was fixed **before building**, in `QuietGate_Architecture_Plan.md` §2 (17 Nov 2026).
> This file was compiled from that plan; the numbers were not changed after measuring.

## The customer's problem, in my own words

A team of 4 to 6 people meets in Korean and English around one shared AI speaker. Today the speaker costs them
meeting time instead of saving it:
- it jumps in whenever there is a pause;
- it starts talking while someone is mid-sentence;
- it keeps going after people tell it to stop;
- it misses people on the far side of the table.

The team will only accept it if, in a real meeting, it **stays quiet until someone calls it by name**, **never talks
over a person**, **stops at once when told**, and **hears everyone**. They pay to get meeting time and decisions back.

## Track and why

**Voice AI track.** Three of the four acceptance conditions are decisions about *when to speak*, and those can be
measured from audio alone, without hardware or a user study. Open models already exist for the hard parts (wake word,
voice activity, keyword recognition). The missing piece is the logic that combines them, plus a fair before/after
measurement. "Hears everyone" is mainly a microphone question (hardware track); we only measure misses by seat
distance as a diagnostic.

## Acceptance test (numbers)

Measured by `python -m quietgate.cli eval` on synthetic meetings.

| Metric | Pass if | Definition |
|---|---|---|
| Uncalled interruptions per 10 min | ≤ 0.5 | assistant starts with no wake call ending in the previous 8 s |
| Talk-over starts | 0 | assistant starts while a human is speaking (ground truth) |
| Missed calls | ≤ 10 % | wake calls with no assistant start within 3 s of the caller finishing |
| Stop latency, p95 | ≤ 0.5 s | end of the stop word → assistant audio stops |
| Stop misses | ≤ 5 % | assistant keeps talking > 1.5 s after a stop word |
| Reply delay after call, median | ≤ 1.5 s | guard metric, so the gate cannot "win" by never speaking |

**Before** = a typical naive assistant: it answers after any 700 ms pause and ignores "stop". Same detectors, same
evaluator. The headline numbers come from a held-out set that was built only after the code was frozen
(see `evidence.md` §3).

## What I left out to fit the time box

- The assistant's brain (LLM, real answers): the reply is a fixed clip.
- "Hears every person" as a hardware problem: seat distance is only imitated with per-speaker gain (0 to −12 dB).
- Acoustic echo cancellation: the evaluation does not feed the reply back into the mic. The live demo uses headphones.
- Training a custom wake word (we reuse the pre-trained "hey_jarvis"), and a learned turn detector (we use a 700 ms
  silence rule).
- Real recordings and the AMI corpus: synthetic voices only (no consent issues, fully reproducible).
