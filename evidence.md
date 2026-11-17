# evidence.md

## 1. The acceptance test (fixed before building)

From `QuietGate_Architecture_Plan.md` §2, written before any code. Copied unchanged into `intent.md`.

| Metric | Pass if | Definition |
|---|---|---|
| Uncalled interruptions per 10 min | ≤ 0.5 | assistant starts with no wake call ending in the previous 8 s |
| Talk-over starts | 0 | assistant starts while a human is speaking (ground truth) |
| Missed calls | ≤ 10 % | wake calls with no assistant start within 3 s of the caller finishing |
| Stop latency, p95 | ≤ 0.5 s | end of the stop word → assistant audio stops |
| Stop misses | ≤ 5 % | assistant keeps talking > 1.5 s after a stop word |
| Reply delay after call, median | ≤ 1.5 s | guard metric, so the gate cannot "win" by never speaking |

**Before** = a typical naive assistant that answers after any 700 ms pause and ignores "stop". It uses the same
detectors (VAD) and the same evaluator.

Added later as **diagnostics** (not part of the pass/fail test, because they were not fixed in advance), for the brief's
other complaints: *cuts sentences in half* (starts inside a caller's mid-sentence pause), *false stops* (reply cut
although nobody said stop) and *one side of the table* (misses split by near vs. far seat).

## 2. What already exists, and what we chose

| Need | Options checked | Chosen | Why |
|---|---|---|---|
| Wake word | Picovoice Porcupine, openWakeWord, Snowboy (archived), cloud wake APIs | **openWakeWord** `hey_jarvis` | Free, offline, no API key, runs on CPU. Porcupine needs an access key; training a custom wake word does not fit 4 h. |
| Voice activity | webrtcvad, Silero VAD, pyannote | **Silero VAD** (bundled with openWakeWord) | More accurate than webrtcvad and language-agnostic; already shipped with openWakeWord, so nothing extra to install. |
| Turn detection | fixed silence rule, LiveKit turn-detector, Pipecat smart-turn | **700 ms silence rule** (our own, tiny) | The learned detectors are English-centred and need a transformer runtime; the silence rule fits the time box. Its weakness is measured (§5). |
| "Stop" and Korean keywords | Whisper / faster-whisper, Vosk, cloud speech APIs | **Vosk** small EN + small KO | Streaming partial results in about 0.1 to 0.4 s on CPU, offline, no key. Whisper is too slow on CPU for a stop under 0.5 s. |
| Test speech | own recordings, AMI corpus, TTS | **edge-tts** neural voices (en-US, ko-KR) | No consent issues, fully reproducible, controllable labels. AMI has no "Hey Jarvis" calls or Korean. |
| Review page | Flask + JS, Streamlit, Gradio | **Gradio** | Pure Python, audio players and file downloads built in. |

**The gap we built:** the turn-taking gate (state machine + "never start during speech" rule), the Korean wake and
stop logic on top of Vosk (v2: grammar mode, short-command rule, honorific rule), the naive baseline, the synthetic
meeting generator with ground truth, the metrics, the evaluator and failure explainer, and the review page.

## 3. How it was verified

- **Two synthetic data sets** (edge-tts voices, 3 to 6 speakers each, Korean and English, seat gains 0 to −12 dB,
  pink noise, about 15 % overlapping turns):
  - **dev** (`data/`, seed 42): 30 meetings, 32.8 min. Used while building v1 and v2 (tune split 0-9, test split 10-29).
  - **held-out** (`data/holdout/`, seed 2026): 24 meetings, 24.1 min, **54 calls (29 Korean), 36 stops (20 Korean)**.
    Every sentence is new, and it adds near-misses aimed at our own rules ("Stop by my desk…", "그만큼…",
    "Travis said…", "자비스라는 업체"), mid-sentence pauses inside calls, and people talking while the assistant answers.
    **It was built after v2 was frozen.** `results/v2_freeze.txt` holds the hashes of the v2 code and config,
    recorded before the held-out set existed, and they still match. Nothing was changed after seeing held-out results.
- **Ground truth** comes from the generator (who spoke when, call/stop intervals), never from a detector.
- **Same inputs for everyone:** detector outputs are cached per scene; baseline, v1 and v2 are scored by the same code.
- **Tests:** 17 (`pytest -q`): gate logic (never starts during speech, stop cuts at once, re-arm after a false wake),
  metric maths, the Korean/English word rules, and a replay of a meeting through the real live-microphone loop
  (fake mic and clock) that must match the offline result exactly.
- **Reproducibility, tested:** a clean install from scratch (`run_project.bat`: new venv, models downloaded, data
  rebuilt) reproduced the QuietGate numbers exactly. Rebuilding audio through edge-tts returned 2 of 135 clips about
  10 ms different, which moved only the naive baseline slightly. **For exact numbers, use the shipped audio**
  (`data/`, `data/holdout/`, also in `quietgate_test_audio.zip` on the review page). Eval reruns are identical;
  detector reruns give identical decisions (raw wake scores differ by at most 0.005 from ONNX float noise).

Reproduce: `run_project.bat` (Windows), or `pip install -r requirements.txt`, `python -m quietgate.cli fetch-models`,
`python -m quietgate.cli eval`, `python -m pytest -q`. The report prints config hashes, labels hashes and versions.

## 4. Before vs after: headline, held-out set (24 meetings, 24.1 min)

| Metric | Target | Before: naive | QuietGate v1 | QuietGate v2 | v2 pass? |
|---|---|---|---|---|---|
| Uncalled interruptions / 10 min | ≤ 0.5 | 20.34 | 1.66 | **4.15** | FAIL |
| Talk-over starts | 0 | 10 | 0 | **1** | FAIL |
| Missed calls | ≤ 10 % | 25.9 % | 16.7 % | **11.1 %** | FAIL |
| Stop latency p95 | ≤ 0.5 s | 6.05 s | 5.70 s | **5.38 s** (p50 **0.11 s**) | FAIL |
| Stop misses | ≤ 5 % | 90 % | 26.7 % | **12.1 %** | FAIL |
| Reply delay, median | ≤ 1.5 s | 1.08 s | 1.07 s | **1.08 s** | PASS |

**In plain words:** compared with a naive assistant, QuietGate v2 interrupts about **5 times less** (49 → 10 uncalled
starts), answers more calls (40 → 48 of 54), and stops when told **7 times more often** (stopped 3 of 30 → 29 of 33),
usually within 0.11 s. But on new, harder sentences it **does not meet any target except reply delay**.

**Korean, the reason for v2:**

| Korean only (held-out) | v1 | v2 |
|---|---|---|
| Missed calls | 24.1 % (7 of 29) | **6.9 % (2 of 29)** |
| Stop misses | 44.4 % (8 of 18) | **16.7 % (3 of 18)** |

v2 trades this for more false wakes: 4 → 10 uncalled starts (see §6).

**Dev set, test split (for continuity; v2 numbers here are optimistic):** v2 passes all six there (uncalled 0.45,
talk-over 0, missed calls 5.6 %, stop p95 0.48 s, stop misses 0 %, delay 1.12 s), against v1's 0.45 / 0 / 11.1 % /
4.43 s / 12.5 % / 1.12 s. Dev failures were inspected while building v2, so we do **not** use these as the result.
The gap between dev and held-out is itself a finding: both versions were fitted to dev more than we realised.

## 5. Diagnostics for the brief's other complaints (held-out set, v2)

| Complaint | Measure | Result |
|---|---|---|
| "Cuts sentences in half" | starts inside a caller's mid-sentence pause | **5 of 25 pauses** (naive: 5, v1: 6). The 700 ms silence rule cannot tell a thinking pause (> 0.7 s) from the end of a turn. |
| False stops | replies cut although nobody said stop | **4** while people talked during 16 replies (v1: 4). Ordinary talk such as "Please don't **stop** the pilot…" and "계약 갱신은…" fired the stop detector. |
| "Misses voices from one side of the table" | missed calls by seat | near seats (0 to −6 dB) 14.8 %, far seats (−6 to −12 dB) 7.4 %. No far-seat penalty at these gains, but gain is only a crude stand-in for distance (no reverberation, real microphones). |

## 6. What still fails (plainly)

From `results/holdout/failures_quietgate_v2.md` (every failure listed with what was said, by whom, and why):

1. **10 uncalled starts, all from the Korean wake path.** The Korean recogniser hears name *mentions* as calls:
   "자비스라는 이름의 업체도 있어요" (5), the English "Jarvis is also the name of our new vendor" (3), "The service desk…"
   (1) and "Hey everyone, sorry I'm a bit late" (1).
   Our 씨 rule catches only one way of mentioning a name. A stricter rule ("헤이 자비스" only) was tried on dev and
   dropped, because it missed calls when people overlapped and the "헤이" was swallowed. **This is a real trade-off we
   did not solve.**
2. **5 sentences cut in half and 3 calls missed as a knock-on effect:** the caller paused > 0.7 s mid-sentence, the
   assistant started, and it was still talking when the real question finished.
3. **8 slow or missed stops:** 4 never recognised in time ("그만해요" twice and "그만" once, all from the same Korean
   voice, plus one English "Stop."),
   and 4 recognised 0.52 to 0.63 s after the word ended, just over the 0.5 s target.
4. **4 false stops** on ordinary talk during the reply (see §5).
5. **1 talk-over start:** someone began speaking in the same 80 ms block in which the assistant started.
6. **Synthetic is cleaner than real:** TTS voices, no room echo, no assistant echo into the mic (the live demo needs
   headphones; no echo cancellation), and seat distance is only a gain change.

## 7. Where AI helped and where it was corrected

AI (Claude Code) wrote most of the code from the architecture plan. Each correction below was caught by an
evaluation, a probe or a test, not by trusting the output. The full list with prompts is in `directive.md`.

| # | AI output | How it was caught | Correction |
|---|---|---|---|
| 1 | Korean stop words via a Vosk grammar without a garbage path | probe: "stop" fired on every Korean sentence | v1: free recognition (v2: grammar + general vocabulary) |
| 2 | Gate ignored a new wake while ARMED | dev trace: a false wake swallowed the real call | re-arm on a new wake, plus a unit test |
| 3 | "Stop" honoured while ARMED | dev: "…decisions **so far**" heard as stop cancelled calls | stop only acts while speaking |
| 4 | Korean mention filter by word position | re-evaluation showed no effect | honorific rule (자비스 + 씨) |
| 5 | Korean wake requiring "헤이 자비스" (first v2 draft) | dev scene_25: overlap swallowed "헤이", call missed | dropped; back to the 씨 rule |
| 6 | v2 vocabulary lacked 씨, so the 씨 rule could never fire | dev: 23 false wakes from "자비스 씨가…" | added honorific words to the vocabulary |
| 7 | The first v2 probe used words taken from the test sentences | noticed in review before reporting | discarded; wrote a general vocabulary and a fresh held-out set |
| 8 | Upload errors exposed a server path; detections listed per 80 ms block; model reloaded per upload | edge-case upload tests | friendly error, one entry per word, model cache |
| 9 | Requested port 6000 | opened in Chrome: blocked (ERR_UNSAFE_PORT) | default port 6060 |

**Disclosure:** v1 and v2 rules were developed while looking at dev-set failures (rules 2 to 6). That is why the
headline comes from the held-out set, which was written afterwards and never tuned on.

## 8. Time spent

> **To fill in by Pulkit before submitting:** the real hours spent (the Quest asks for at most 4).
> Also state honestly whether the v2 work and the held-out set (§4) were done after the 4-hour mark.

| Phase | Time |
|---|---|
| Acceptance test + checking existing tools | _ |
| Build v1 + first measurement | _ |
| Testing, v2 and held-out evaluation | _ |
| Docs + Loom | _ |

## 9. Next test

1. **Real room:** 4 to 6 consenting people at real seat distances, Korean and English, same six numbers plus the
   three diagnostics. Or, first, an AMI far-field excerpt for false wakes.
2. **Name mentions vs. calls (the main open failure):** train a custom openWakeWord model for "헤이 자비스" (it
   supports synthetic training data) and drop the Korean ASR wake path. Measure uncalled starts and Korean missed
   calls on a *new* held-out set.
3. **Mid-sentence pauses:** replace the fixed 700 ms rule with a learned end-of-turn model and re-measure cut-ins.
4. **False stops:** require the stop command to be its own short utterance (silence before and after) and count wrong
   cuts while people talk during replies.
5. **Echo:** play the reply through the real speaker (with echo cancellation) and measure false stops and false speech.
