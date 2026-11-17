# QuietGate

Architecture and build plan for a speak-only-when-called gate for a shared meeting voice assistant (MatchHire Quest "Quiet Until Called", Voice AI track)

Author: Pulkit Chadha  |  Date: 17 Nov 2026  |  Time box: 4 hours  |  Audience: Claude Code (implementer) and the reviewer

## 1. What we are building

A meeting team of 4 to 6 people (Korean and English) shares one AI speaker. They reject it because it talks over people, cuts sentences in half and will not shut up. **QuietGate** is a small Python layer that sits between the microphone and the assistant's voice and decides one thing: **may the assistant speak right now?**

The gate enforces three rules:

1. **Called by name only.** The assistant stays silent unless someone says the wake phrase ("Hey Jarvis").
2. **Never during someone else's turn.** After the call, it waits until the person finishes speaking before replying, and never starts while anyone is talking.
3. **Stops at once.** While speaking, it stops within 500 ms when someone says "stop" / "그만" / "멈춰".

We do not build the assistant's brain (no LLM, no answers). The "reply" is a pre-recorded clip. The deliverable is the gate plus a reproducible evaluation that shows before vs after numbers.

## 2. Acceptance test (written before building)

All numbers are measured by `quietgate eval` on the fixed synthetic test set (seed 42). The **baseline** is a typical naive assistant: it replies after any 700 ms pause in speech and ignores "stop" until its reply ends.

| Metric | Target (pass) | Baseline (expected) | How it is computed |
| --- | --- | --- | --- |
| Uncalled interruptions per 10 min | ≤ 0.5 | High (every pause) | Assistant speech starts with no wake call in the preceding 8 s, normalised to 10 min of audio |
| Talk-over starts | 0 | > 0 | Assistant starts while ground-truth human speech is active |
| Missed calls | ≤ 10% | N/A (no wake logic) | Labelled wake calls with no assistant start within 3 s of the caller finishing |
| Stop latency (p95) | ≤ 500 ms | = remaining reply length | Time from end of "stop" word to assistant audio stopping |
| Stop misses | ≤ 5% | 100% | Stop commands after which the assistant keeps talking > 1.5 s |
| Reply delay after call (median) | ≤ 1.5 s | ~0.7 s | Guard metric: keeps the gate from becoming silent and useless |

**Out of scope:** share of seats heard correctly (that is the hardware track). We note it as the next test in evidence.md.

## 3. What we reuse vs what we build

| Need | Reused (public, open-source) | Why this choice |
| --- | --- | --- |
| Wake phrase | openWakeWord, pre-trained "hey_jarvis" model, ONNX runtime | Free, offline, no API key, runs on CPU. Training a custom name does not fit 4 h. |
| Is someone talking? (VAD) | Silero VAD ONNX model via onnxruntime (fallback: webrtcvad) | Accurate and language-agnostic; ONNX avoids installing PyTorch. |
| "Stop" in Korean and English | Vosk with grammar restricted to stop words; small EN and KO models | Grammar mode only listens for a few words, so it is fast and rarely misfires. Partial results give low latency. |
| Test speech | edge-tts (en-US and ko-KR neural voices, no key) | Synthetic voices avoid any consent problem. Optional: AMI Meeting Corpus clip for false-trigger testing. |
| Audio I/O | soundfile (files), sounddevice (live demo only) | Minimal, cross-platform. |

**The gap we build ourselves:** (a) the turn-taking state machine that combines the three signals, (b) the playback controller that can cut audio mid-clip, (c) the scenario generator with ground-truth labels, (d) the evaluator and the naive baseline.

## 4. System architecture

### 4.1 Data flow

```
  mic / wav file (16 kHz mono, int16)
          |
          v
   AudioSource  --- 80 ms blocks (1280 samples), each tagged with a timestamp
          |
          +--> VadDetector        -> speech_prob, is_speech (with hangover)
          +--> WakeDetector       -> wake score, wake_event
          +--> StopDetector       -> stop_event (from Vosk partial result)
          |
          v
     Signals(t, is_speech, wake, stop)
          |
          v
     TurnGate (state machine)  ---> GateEvent: START_SPEAKING / STOP_SPEAKING
          |
          v
     PlaybackController  (live: sounddevice; eval: simulated timeline)
          |
          v
     EventLog (JSONL)  ---> Evaluator ---> results/metrics.json + report.md
```

### 4.2 Gate state machine

| State | Meaning | Transitions |
| --- | --- | --- |
| IDLE | Silent, listening for the wake phrase only | wake_event → ARMED (record call time) |
| ARMED | Called; waiting for the caller to finish their sentence | is_speech false for ≥ end_of_turn_ms (700) → SPEAKING (emit START). No end of turn within armed_timeout_s (8) → IDLE. stop_event → IDLE. |
| SPEAKING | Playing the reply | stop_event → IDLE (emit STOP immediately). Reply finished → IDLE. Optional yield rule: other speech for ≥ yield_ms (600) → IDLE (emit STOP), off by default in live mode because of speaker echo. |

Hard rule checked in code: START is never emitted while `is_speech` is true. Wake detection is ignored for `refractory_s` (2 s) after an event to avoid double triggers.

### 4.3 Baseline (for the "before" numbers)

`NaiveGate`: emits START whenever is_speech has been false for 700 ms after any speech, plays the full reply, and ignores stop. It uses the same detectors and the same evaluator, so the comparison is fair.

## 5. Repository layout

```
quietgate/
  README.md                 # what it is, one-command reproduce, results table
  intent.md  directive.md  evidence.md
  pyproject.toml            # python >=3.10, pinned versions
  config/default.yaml       # thresholds and timings (single source of truth)
  quietgate/
    __init__.py
    audio.py                # AudioSource: WavSource, MicSource; block iterator
    detectors/
      vad.py                # VadDetector (Silero ONNX, fallback webrtcvad)
      wake.py               # WakeDetector (openWakeWord hey_jarvis, onnx)
      stop.py               # StopDetector (Vosk grammar: stop, 그만, 멈춰)
    gate.py                 # TurnGate + NaiveGate, pure logic, no audio deps
    playback.py             # PlaybackController (live + simulated)
    pipeline.py             # wires source -> detectors -> gate -> playback
    eval/
      scenarios.py          # synthetic scene generator + labels.json
      metrics.py            # metric functions (pure, unit-tested)
      run_eval.py           # runs both gates over the test set
    cli.py                  # quietgate {fetch-models,make-data,eval,live}
  assets/reply_en.wav       # canned assistant reply (generated by edge-tts)
  data/                     # generated scenes (gitignored except labels)
  results/                  # metrics.json, report.md, events/*.jsonl
  tests/
    test_gate.py            # state machine on hand-made Signals sequences
    test_metrics.py         # metric math on tiny fixed timelines
  Makefile                  # setup, data, eval, test, live
```

## 6. Module contracts

Keep the gate and metrics free of audio libraries so they can be unit-tested with plain lists.

```
@dataclass
class Signals:
    t: float            # seconds from start of stream (block end time)
    is_speech: bool
    wake: bool
    stop: bool

class GateEvent(Enum): START = "start"; STOP = "stop"

class TurnGate:
    def __init__(self, cfg: GateConfig): ...
    def step(self, s: Signals, reply_done: bool) -> list[tuple[float, GateEvent]]: ...
    state: Literal["IDLE", "ARMED", "SPEAKING"]

class VadDetector:  def process(self, block: np.ndarray) -> bool
class WakeDetector: def process(self, block: np.ndarray) -> bool   # score >= wake_threshold
class StopDetector: def process(self, block: np.ndarray) -> bool   # partial result hits grammar word
```

Event log line (JSONL): `{"t": 12.48, "gate": "quiet", "event": "start", "state_from": "ARMED"}`

## 7. Test data (synthetic, reproducible)

- `quietgate make-data --seed 42 --n 30` builds 30 scenes, each 60 to 90 s, total about 40 minutes.
- Each scene mixes 3 to 5 synthetic speakers (en-US and ko-KR edge-tts voices) taking turns with short pauses (300 to 1200 ms), plus some overlaps, at different gains (-0 to -12 dB) to imitate near and far seats. Low pink noise is added.
- Scene types: **no-call** (meeting chatter, including near-miss words like "Jarvis said" or "service"), **call** ("Hey Jarvis, what is on the agenda?"), **call + stop** (someone says "stop" or "그만" 1 to 3 s after the expected reply start).
- `data/labels.json` stores per scene: speech segments per speaker, wake-call intervals, stop-word intervals. Labels come from the generator, not from detectors, so they are true ground truth.
- Simulation detail: in eval the reply is not mixed into the mic audio (no echo). Stop commands are placed relative to the label "expected reply start" so stop latency is measurable even if the gate is slightly early or late.
- Optional (only if time remains): one AMI Mix-Headset meeting excerpt with no calls, used only for the false-trigger rate.

Generated audio is cached; edge-tts needs internet the first time. Commit `labels.json` and the generator so anyone can rebuild identical data.

## 8. Configuration (config/default.yaml)

```
sample_rate: 16000
block_ms: 80
vad:   { backend: silero, threshold: 0.5, hangover_ms: 200 }
wake:  { model: hey_jarvis, threshold: 0.5, refractory_s: 2.0 }
stop:  { words_en: [stop], words_ko: ["그만", "멈춰"], use_partial: true }
gate:  { end_of_turn_ms: 700, armed_timeout_s: 8.0, yield_ms: 600, yield_enabled_eval: false }
eval:  { seed: 42, uncalled_window_s: 8.0, missed_call_window_s: 3.0, stop_miss_s: 1.5 }
```

## 9. CLI and reproducibility

```
pip install -e .
quietgate fetch-models        # openWakeWord, Silero ONNX, Vosk en + ko (small) into ./models
quietgate make-data --seed 42 # builds data/ and labels.json
quietgate eval                # runs NaiveGate and TurnGate, writes results/
quietgate live                # mic demo for the Loom (use headphones)
pytest -q
```

`results/report.md` prints a before/after table with the targets and a PASS/FAIL per metric, plus the commit hash, config hash and model versions, so a reviewer can rerun and get the same numbers.

## 10. Build phases for Claude Code (4-hour budget)

| Time | Work | Done when |
| --- | --- | --- |
| 0:00–0:30 | Write intent.md (problem, metrics table from section 2, track, exclusions). Scaffold repo, pyproject, config, CLI stubs. | pip install -e . works; quietgate --help lists 4 commands. |
| 0:30–1:30 | gate.py (TurnGate + NaiveGate) and metrics.py with unit tests first. Then detectors and fetch-models. | pytest passes; each detector fires on a one-line test wav. |
| 1:30–2:30 | scenarios.py, labels, run_eval.py, report. First full eval run. | results/report.md shows before and after numbers. |
| 2:30–3:15 | Tune thresholds on 10 scenes only, re-measure on the other 20 (no tuning on the test split). Live mic mode. | Live demo: call, reply, stop works on a laptop mic. |
| 3:15–4:00 | evidence.md, directive.md, README, record Loom. | All five deliverables ready. |

If time runs short, cut in this order: AMI clip → yield rule → live mode polish. Never cut the baseline or the reproducible eval.

## 11. Instructions to give Claude Code

Paste this as the first message, together with this document:

```
You are implementing "QuietGate" exactly as described in the attached plan.
Rules:
1. Python 3.10+, Windows and Linux compatible. Minimal dependencies:
   numpy, soundfile, onnxruntime, openwakeword, vosk, edge-tts, pyyaml,
   sounddevice (live only), pytest. Do not add torch, cloud APIs or API keys.
2. Use openWakeWord with inference_framework="onnx" (tflite is not
   available on Windows).
3. Write gate.py and metrics.py first, with unit tests, before any audio code.
   The gate must never emit START while is_speech is true; add a test for it.
4. All thresholds come from config/default.yaml. No magic numbers in code.
5. Everything must be reproducible from a clean clone with the commands in
   section 9. Fix the random seed. Print model names and versions in the report.
6. Split scenes into tune (10) and test (20). Report metrics on test only.
7. Do not invent results. If a metric fails its target, report FAIL and why.
8. After each phase, run pytest and quietgate eval and show me the output
   before moving on.
```

Record every prompt and every correction you make in directive.md as you go (the Quest scores this).

## 12. Risks and what may still fail

| Risk | Mitigation / honest note |
| --- | --- |
| "Hey Jarvis" said with Korean accent is missed | Include ko-KR voices saying the English wake phrase in the test set and report misses per language. |
| Synthetic voices are cleaner than real rooms | State it plainly in evidence.md. Next test: real recording with consenting people, or AMI far-field mix. |
| Speaker echo triggers barge-in in live mode | Use headphones in the demo; yield rule off in live mode. Acoustic echo cancellation is out of scope. |
| Vosk misses short "stop" | Use partial results, include stop-word variants, report stop-miss rate per language. |
| Far seats (low gain) missed by VAD/wake | Report metrics per gain bucket; this is the bridge to the hardware track. |
| End-of-turn = 700 ms silence cuts slow speakers | Report a sweep (500/700/1000 ms) in evidence.md; a learned turn detector (e.g. LiveKit turn-detector) is the next step. |

## 13. Deliverable checklist

- Public GitHub repo (the working deliverable link) with README results table.
- intent.md: problem in own words, numeric acceptance test, why Voice track, what was cut.
- directive.md: the prompts above plus every correction made to AI output.
- evidence.md: metrics before/after, reproduce commands, reused vs built, AI help vs corrections, what still fails, next test.
- Loom (≤ 5 min): problem → live demo (silence during chatter, call, reply, "stop") → eval table → what fails → next test.
- Security check: no API keys, no personal recordings, data/ generated only from synthetic voices.