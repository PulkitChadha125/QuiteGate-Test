# QuietGate

**A speak-only-when-called gate for a shared meeting voice assistant** (MatchHire Quest "Quiet Until Called", Voice AI track).

A meeting team of 4 to 6 people (Korean and English) shares one AI speaker. They reject it because it
talks when nobody asked, talks over people, and will not stop when told. QuietGate is a small Python layer
between the microphone and the assistant's voice. It decides one thing: **may the assistant speak right now?**

| Rule | How |
|---|---|
| 1. Speak only when called by name | "Hey Jarvis" (openWakeWord) or Korean "헤이 자비스" (Vosk KO grammar); "자비스 씨가…" (a mention) is ignored |
| 2. Never during someone else's turn | After the call, wait until nobody has spoken for 700 ms (Silero VAD). Never start while speech is detected. |
| 3. Stop at once when told | "stop" / "그만" / "멈춰" (Vosk EN + KO) as one of the first two words of an utterance cuts the reply in the next 80 ms block |

We do **not** build the assistant's brain. The "reply" is one pre-recorded clip. The deliverable is the gate
plus a reproducible evaluation with before-and-after numbers.

## Results: held-out set (24 new synthetic meetings, 24.1 min, built after the code was frozen)

| Metric | Target | Before (naive) | QuietGate v1 | QuietGate v2 (current) | |
|---|---|---|---|---|---|
| Uncalled interruptions / 10 min | ≤ 0.5 | 20.34 | 1.66 | **4.15** | FAIL |
| Talk-over starts | 0 | 10 | 0 | **1** | FAIL |
| Missed calls | ≤ 10 % | 25.9 % | 16.7 % | **11.1 %** | FAIL |
| Stop latency p95 | ≤ 0.5 s | 6.05 s | 5.70 s | **5.38 s** (p50 0.11 s) | FAIL |
| Stop misses | ≤ 5 % | 90 % | 26.7 % | **12.1 %** | FAIL |
| Reply delay after call (median) | ≤ 1.5 s | 1.08 s | 1.07 s | **1.08 s** | PASS |

Against a naive assistant, v2 interrupts about 5 times less, answers more calls (48 vs 40 of 54) and obeys "stop"
29 of 33 times instead of 3 of 30. v2 fixed most of the Korean problem: Korean missed calls fell from 24 % to 7 %, and
Korean stop misses from 44 % to 17 %. **It still does not pass the acceptance test on new sentences.** The main
remaining failure is that it wakes on name *mentions* ("자비스라는 업체", "Jarvis is our vendor"). On the dev set that
v2 was built on, it passes all six targets; that number is optimistic and not the headline.
Full details: [`evidence.md`](evidence.md), [`results/report.md`](results/report.md),
[`results/holdout/failures_quietgate_v2.md`](results/holdout/failures_quietgate_v2.md).

## How it works

```
 mic / wav (16 kHz mono) ──► 80 ms blocks
        │
        ├─► Silero VAD (reused)        → is anyone talking?
        ├─► openWakeWord (reused)      → "Hey Jarvis"?
        └─► Vosk EN + KO (reused)      → "stop" / "그만" / "멈춰"?  "자비스"?
                    │                    (KO: grammar = keywords + general vocabulary, config/ko_vocab.txt)
                    ▼
        TurnGate state machine (built)       IDLE ──wake──► ARMED ──700 ms silence──► SPEAKING
                    │                         ▲                                         │
                    ▼                         └────────── stop word / reply done ───────┘
        playback (live: speaker, eval: simulated timeline)
                    ▼
        evaluator (built) → before/after metrics vs ground-truth labels
```

**Reused:** openWakeWord `hey_jarvis`, Silero VAD (bundled with openWakeWord), Vosk small EN + KO, edge-tts, Gradio.
**Built (the gap):** the turn-taking gate, the Korean wake/stop logic, the naive baseline, the synthetic meeting
generators with ground truth, the metrics, evaluator and failure explainer, and the review page.
What else was considered and why it was not used: `evidence.md` §2.

## Quick start (Windows)

Double-click **`run_project.bat`**, or run it from a terminal:

```bat
run_project.bat          :: port 6060 (default)
run_project.bat 7000     :: custom port
```

It creates `.venv`, installs `requirements.txt`, downloads the models, builds any missing test data (needs internet
once), runs the tests and the evaluation, then starts the review page at `http://localhost:6060`.

> **Exact numbers:** the test audio is shipped in `data/` and `data/holdout/` (and in `quietgate_test_audio.zip` on the
> review page). With it in place, nothing is rebuilt and the numbers match exactly. Rebuilding the audio through
> edge-tts can return a few clips a few milliseconds different, which moves the naive baseline slightly.

## Manual steps (Windows / Linux / macOS, Python 3.10+)

```bash
python -m venv .venv
.venv\Scripts\activate           # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

python -m quietgate.cli fetch-models    # openWakeWord + Silero VAD + Vosk EN/KO (about 80 MB download, 330 MB unpacked)
python -m quietgate.cli make-data       # only if data/ is missing: dev (seed 42) + held-out (seed 2026) meetings
python -m pytest -q                     # 17 tests (gate, metrics, word rules, live-loop replay)
python -m quietgate.cli eval            # naive vs v1 vs v2 on dev + held-out -> results/report.md
python -m quietgate.diagnose            # every v2 failure on the held-out set -> results/holdout/failures_quietgate_v2.md
python app.py --port 6060               # review page
python -m quietgate.cli live            # live microphone demo with v2 (use headphones)
```

## The review page (`app.py`)

| Tab | What it shows |
|---|---|
| 1. Results | The before/after tables (from `results/report.md`) |
| 2. Listen to a test scene | Any held-out or dev meeting: timeline of who spoke, calls, stops, and when naive / v1 / v2 talked. Two players (naive vs v2) with the reply mixed in. |
| 3. Try your own audio | Upload a WAV/FLAC/OGG/MP3 (any sample rate, mono or stereo, max 3 min); naive and v2 run on it. About 25 s per minute of audio. |
| 4. Raw files | Source + results zip, test-audio zip, and the individual documents |
| 5. Docs | evidence.md, intent.md, directive.md, README |

**Hosting on a server:** `run_project.bat` (or `python app.py --host 0.0.0.0 --port 6060`), open TCP 6060 in the
firewall, and send the client `http://<server-ip>:6060`. **Do not use port 6000:** Chrome, Edge and Firefox refuse to
open it (`ERR_UNSAFE_PORT`; the same applies to 6665-6669, 6697 and 10080). The page needs no microphone, so plain HTTP
works. The live microphone demo is a terminal program and runs on the presenter's laptop.

## Project layout

```
config/default.yaml        v2: every threshold and timing (single source of truth)
config/v1.yaml             v1, frozen, for the comparison
config/ko_vocab.txt        general Korean vocabulary for the v2 Vosk grammar
quietgate/gate.py          TurnGate (QuietGate) + NaiveGate (baseline) + simulator - pure logic
quietgate/detectors.py     wrappers around Silero VAD, openWakeWord, Vosk + the word rules
quietgate/metrics.py       acceptance-test metrics + diagnostics - pure functions
quietgate/scenarios.py     dev meeting generator (seed 42)
quietgate/holdout.py       held-out meeting generator (seed 2026, new sentences)
quietgate/run_eval.py      runs naive / v1 / v2 on both sets, writes results/
quietgate/diagnose.py      explains each failure
quietgate/live.py          microphone demo
quietgate/cli.py           command line
app.py                     Gradio review page
tests/                     17 tests
data/, data/holdout/       test audio (scenes/*.flac) + ground truth (labels.json)
results/                   report.md, v2_freeze.txt, dev/ and holdout/ (metrics, timelines, failures, events)
intent.md evidence.md directive.md loom_script.md   Quest documents
```

## Data and safety

- All speech is synthetic (Microsoft edge-tts neural voices). No person was recorded.
- No API keys, no cloud APIs at run time; edge-tts is used only to build the test data. Gradio usage analytics are off.
- Uploaded files on the review page are processed in memory and not stored by the app (Gradio keeps a temporary
  copy in its cache folder).
