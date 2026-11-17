# evidence.md

## 1. Acceptance test

See `intent.md` (fixed before building): uncalled interruptions ≤ 0.5 / 10 min, talk-over starts = 0, missed
calls ≤ 10 %, stop latency p95 ≤ 0.5 s, stop misses ≤ 5 %, median reply delay ≤ 1.5 s.

## 2. How it was verified

- **Test data:** 30 synthetic meeting scenes (32.8 min, seed 42) from `quietgate/scenarios.py`. Each scene has 3 to 5
  speakers (5 en-US + 3 ko-KR edge-tts neural voices) taking turns with 0.3 to 1.2 s pauses and about 15 % overlaps.
  Each speaker has a seat gain of 0 to -12 dB, and low pink noise is added. There are three scene types: chatter only,
  "Hey Jarvis" calls, and calls followed by "stop" / "그만" / "멈춰" / "그만해". The chatter includes near-misses:
  "Jarvis said…", "customer service", "jars", "we should stop spending…", "자비스 씨가…".
- **Ground truth** comes from the generator (speech intervals, call and stop intervals), never from a detector.
- **Split:** scenes 0 to 9 = tune (used for diagnosis and fixes), scenes 10 to 29 = test (the headline numbers).
  The test split has 18 calls (8 EN, 10 KO) and 9 stop commands.
- **Fair comparison:** detectors run once per scene and their outputs are cached. The baseline, QuietGate and the
  ablation all see the same detector outputs.
- **Tests:** 15 (`pytest -q`). One replays a scene through the real live-microphone loop (fake mic and clock) and
  checks it starts and stops at the same moments as the offline eval. The others include "never starts while someone is speaking", "stop cuts immediately",
  "a new wake re-arms after a false wake", and Korean call vs. mention.

**Reproduce:** `run_project.bat`, or `fetch-models → make-data → eval` (see README). The report prints the config
hash, the labels.json hash and the package versions.

Reproducibility was **tested**, not assumed:
- Re-running the eval gives identical metrics.
- Re-running the detectors on the same audio gives identical yes/no decisions. Only the raw wake score varies,
  by up to 0.005, which is ONNX floating-point noise against a threshold of 0.5.
- A **clean install from scratch** (new folder, new venv, models downloaded, data rebuilt via `run_project.bat`)
  reproduced every QuietGate number exactly. edge-tts returned 2 of 135 clips about 10 ms different, which moved
  the *baseline* slightly (uncalled 22.45 → 22.9 per 10 min, talk-over 11 → 9, missed calls 16.7 % → 22.2 %).
  For exact numbers, use the shipped audio (`quietgate_test_audio.zip` on the review page).

## 3. Before vs after (test split, 20 scenes, 22.3 min)

| Metric | Target | Before: naive | After: QuietGate | Pass? | Ablation: openWakeWord only |
|---|---|---|---|---|---|
| Uncalled interruptions / 10 min | ≤ 0.5 | 22.45 | **0.45** | PASS | 0 |
| Talk-over starts | 0 | 11 | **0** | PASS | 0 |
| Missed calls | ≤ 10 % | 16.7 % | **11.1 %** | FAIL | 55.6 % |
| Stop latency p95 | ≤ 0.5 s | 6.15 s | **4.43 s** | FAIL | 5.28 s |
| Stop misses | ≤ 5 % | 100 % | **12.5 %** | FAIL | 20 % |
| Reply delay, median | ≤ 1.5 s | 1.15 s | **1.12 s** | PASS | 1.05 s |

Detail: the assistant spoke 67 times without the gate (50 of them uncalled) and 17 times with it (1 uncalled).
Missed calls by language: **EN 0 of 8, KO 2 of 10**. Stop misses: **EN 0 of 3, KO 1 of 5**. Median stop latency
is 0.38 s. The ablation column shows why the Korean extension matters: openWakeWord alone misses most Korean
calls, because a Korean speaker says "헤이 자비스" with Korean phonetics.

## 4. What still fails (plainly)

From `results/failures_test.md`:

1. **2 missed Korean calls:** "헤이 자비스, 남은 시간이 얼마야?" by two Korean voices. openWakeWord scores 0.00, and
   Vosk KO hears something else (for example "헤이 자릿세"). A Korean-trained wake model is the real fix.
2. **1 missed stop:** "그만해." (SunHi voice), never recognised by the small Vosk KO model. With only 8 measurable
   stops, this one miss pushes **both** the stop p95 (4.43 s) and the stop-miss rate (12.5 %) over target. Two more
   Korean stops were caught but slowly (0.66 s, 0.75 s). The small Korean model is slower than the English one.
3. **1 uncalled start:** "자비스 씨가 보고서를…" ("Jarvis-ssi said…"). Vosk dropped the "씨", so the mention looked like a call.
4. **The stop detector also fires on normal talk.** In the test chatter it fired about 25 times per 10 minutes, mostly
   the English recogniser forcing similar-sounding words into "stop". It did **not** cut any reply here (0 wrong
   cuts), because the test meetings go quiet while the assistant answers. In a real meeting, someone talking over the
   reply could make it stop for no reason. **This is not measured by the current acceptance test** and is the first
   thing to add ("false stops per 10 min while people talk during the reply").
5. **The numbers are small:** 18 calls and 8 measurable stops. One event moves a rate by 5 to 12 points, so treat
   the rates as indicative.
6. **Synthetic is cleaner than real:** TTS voices, no reverberation, no echo of the assistant's own voice, gain-only
   "far seats". Real rooms will be worse, especially for far seats and with laptop speakers (no echo cancellation).

## 5. What was reused vs built

| Reused (open source) | Built (the gap) |
|---|---|
| openWakeWord `hey_jarvis_v0.1` (ONNX) | `TurnGate` state machine (IDLE → ARMED → SPEAKING, hard "no start during speech" rule) |
| Silero VAD (ONNX, bundled with openWakeWord) | Korean wake rule: accept "자비스" from Vosk KO, but not when followed by the honorific 씨 |
| Vosk small EN (grammar mode) + small KO (free mode) | Stop-word logic (fire once per word, prefix match for 그만해 / 멈춰요) |
| edge-tts voices for synthetic speech | Naive baseline, scene generator with ground truth, metrics, evaluator, failure report |
| Gradio for the review page | Review page: timelines and before/after audio per scene |

## 6. Where AI helped and where I corrected it

AI (Claude Code) wrote most of the code from the architecture plan. The evaluation and diagnosis caught these
errors, and each was corrected:

1. **The Korean stop grammar fired on every sentence.** The first version gave Vosk KO a stop-word grammar. That
   model has no `[unk]` token, so every sound became "그만" or "멈춰". A probe on single phrases showed stop hits on
   normal sentences. *Fix:* free recognition for KO and token matching.
2. **A false wake swallowed a real call** (scene_02, tune split). In ARMED state, new wake events were ignored.
   A false wake followed by a real "Hey Jarvis" timed out and missed the call. *Fix:* re-arm on a new wake, plus a unit test.
3. **"…decisions so far" was heard as "stop"** and cancelled the call while ARMED (3 English calls missed despite a
   wake score of 1.00). *Fix:* stop words only act while the assistant is speaking.
4. **The first Korean mention filter did not work.** The rule "the name must not be the first word" failed because
   Vosk merges consecutive sentences. *Fix:* the honorific rule (자비스 + 씨 = a mention). **Disclosure:** this rule was
   chosen after looking at failures of the "자비스 씨가…" near-miss sentence, and the same sentence also appears in
   the test split, so the test number for it is optimistic.
5. The first scene-planning loop that the AI wrote was tangled. It was rewritten before any data was generated.

No thresholds were tuned on the test split. All fixes came from the tune split or from single-phrase probes.
The test numbers were looked at to write this section, but nothing was changed after that.

## 7. Next test

1. **Real room recording** with 4 to 6 consenting people at real seat distances (or an AMI far-field excerpt for
   false triggers). Measure the same six numbers.
2. **A Korean wake word:** train a custom openWakeWord model for "헤이 자비스" (synthetic training data is supported),
   and use a larger Korean ASR model for 그만해 / 멈춰. Rerun to see whether KO missed calls and stops reach target.
3. **More events:** 100+ calls and 50+ stops, so the rates mean something.
4. **False stops:** add chatter during the assistant's reply to the scenes and count wrongly cut replies.
5. **Echo:** play the reply through the actual speaker and measure false stops and false "speech" (needs AEC).
6. **End-of-turn:** sweep 500 / 700 / 1000 ms, and try a learned turn detector for slow speakers.
