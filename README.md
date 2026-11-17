# QuietGate

**A speak-only-when-called gate for a shared meeting voice assistant** (MatchHire Quest "Quiet Until Called", Voice AI track).

A meeting team of 4 to 6 people (Korean and English) shares one AI speaker. They reject it because it
talks when nobody asked, talks over people, and will not stop when told. QuietGate is a small Python layer
between the microphone and the assistant's voice. It decides one thing: **may the assistant speak right now?**

| Rule | How |
|---|---|
| 1. Speak only when called by name | Wake phrase "Hey Jarvis" (openWakeWord) or Korean "헤이 자비스" (Vosk KO) |
| 2. Never during someone else's turn | After the call, wait until nobody has spoken for 700 ms (Silero VAD). Never start while speech is detected. |
| 3. Stop at once when told | "stop" / "그만" / "멈춰" (Vosk EN + KO) cuts the reply in the next 80 ms block |

We do **not** build the assistant's brain. The "reply" is one pre-recorded clip. The deliverable is the gate
plus a reproducible evaluation with before-and-after numbers.

## Results (test split: 20 synthetic scenes, 22.3 min)

| Metric | Target | Before (naive assistant) | After (QuietGate) | |
|---|---|---|---|---|
| Uncalled interruptions / 10 min | ≤ 0.5 | 22.45 | **0.45** | PASS |
| Talk-over starts | 0 | 11 | **0** | PASS |
| Missed calls | ≤ 10 % | 16.7 % | **11.1 %** (2 of 18) | FAIL (close) |
| Stop latency p95 | ≤ 0.5 s | 6.15 s | **4.43 s** (p50 0.38 s) | FAIL |
| Stop misses | ≤ 5 % | 100 % | **12.5 %** (1 of 8) | FAIL |
| Reply delay after call (median) | ≤ 1.5 s | 1.15 s | **1.12 s** | PASS |

What still fails, plainly: some Korean voices saying "헤이 자비스" are not recognised (2 missed calls), and one
Korean "그만해" was never recognised by the small Vosk Korean model. With only 8 measurable stops, that single
miss sets both the stop p95 and the stop-miss rate. English: 0 missed calls (0 of 8), 0 missed stops (0 of 3).
Full details are in [`evidence.md`](evidence.md), [`results/report.md`](results/report.md) and
[`results/failures_test.md`](results/failures_test.md).

## How it works

```
 mic / wav (16 kHz mono) ──► 80 ms blocks
        │
        ├─► Silero VAD (reused)        → is anyone talking?
        ├─► openWakeWord (reused)      → "Hey Jarvis"?
        └─► Vosk EN + KO (reused)      → "stop" / "그만" / "멈춰"?  "헤이 자비스"?
                    │
                    ▼
        TurnGate state machine (built)       IDLE ──wake──► ARMED ──700 ms silence──► SPEAKING
                    │                         ▲                                         │
                    ▼                         └────────── stop word / reply done ───────┘
        playback (live: speaker, eval: simulated timeline)
                    ▼
        evaluator (built) → before/after metrics vs ground-truth labels
```

**Reused:** openWakeWord `hey_jarvis` model, Silero VAD (bundled with openWakeWord), Vosk small EN + KO models,
edge-tts synthetic voices, Gradio.
**Built (the gap):** the turn-taking gate, the Korean wake/stop word logic, the naive baseline, the
synthetic-meeting generator with ground-truth labels, the metrics and evaluator, and the review page.

## Quick start (Windows)

Double-click **`run_project.bat`**, or run it from a terminal:

```bat
run_project.bat          :: port 6060 (default)
run_project.bat 7000     :: custom port
```

It creates `.venv`, installs `requirements.txt`, downloads the models, builds the test data (first time only,
needs internet), runs the unit tests and the evaluation, then starts the review page at `http://localhost:6060`.

> **Exact numbers:** to reproduce the reported numbers exactly, unzip `quietgate_test_audio.zip` (from the review
> page) into the project folder before running. The bat file then skips rebuilding the audio. Rebuilding with
> edge-tts gave 2 of 135 voice clips about 10 ms different in our clean-install test. QuietGate's numbers were
> unchanged, but the baseline's moved slightly (e.g. 22.45 → 22.9 uncalled per 10 min).

## Manual steps (Windows / Linux / macOS, Python 3.10+)

```bash
python -m venv .venv
.venv\Scripts\activate           # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

python -m quietgate.cli fetch-models    # openWakeWord + Silero VAD + Vosk EN/KO (about 80 MB download, 330 MB unpacked)
python -m quietgate.cli make-data       # 30 synthetic scenes + data/labels.json (seed 42)
python -m pytest -q                     # 15 tests (gate, metrics, word logic, live-loop replay)
python -m quietgate.cli eval            # baseline vs QuietGate -> results/report.md
python -m quietgate.diagnose            # every failure explained -> results/failures_test.md
python app.py --port 6060               # review page
python -m quietgate.cli live            # live microphone demo (use headphones)
```

## The review page (`app.py`)

| Tab | What it shows |
|---|---|
| 1. Results | The before/after table (from `results/report.md`) |
| 2. Listen to a test scene | Timeline of who spoke, the calls and stops, and when each gate let the assistant talk. Two audio players (before / after) with the reply mixed in. |
| 3. Try your own audio | Upload a WAV/FLAC/OGG/MP3 (any sample rate, mono or stereo, max 3 min); both gates run on it. Takes about 25 s per minute of audio. |
| 4. Raw files | Source + results zip, test-audio zip, and the individual documents |
| 5. Docs | evidence.md, intent.md, README |

**Hosting on a server:** `run_project.bat` (or `python app.py --host 0.0.0.0 --port 6060`), open TCP 6060 in the
firewall, and send the client `http://<server-ip>:6060`. **Do not use port 6000:** Chrome, Edge and Firefox
refuse to open it (`ERR_UNSAFE_PORT`; the same applies to 6665-6669, 6697 and 10080). The page needs no microphone, so plain HTTP works. The live microphone demo
is a terminal program (`quietgate.cli live`) and runs on the presenter's laptop.

## Project layout

```
config/default.yaml        every threshold and timing (single source of truth)
quietgate/gate.py          TurnGate (QuietGate) + NaiveGate (baseline) + simulator - pure logic
quietgate/detectors.py     wrappers around Silero VAD, openWakeWord, Vosk
quietgate/metrics.py       acceptance-test metrics - pure functions
quietgate/scenarios.py     synthetic meeting generator + ground-truth labels
quietgate/run_eval.py      runs all gates on all scenes, writes results/
quietgate/diagnose.py      explains each failure
quietgate/live.py          microphone demo
quietgate/cli.py           command line
app.py                     Gradio review page
tests/                     unit tests
data/labels.json           ground truth (data/scenes/*.flac = the test audio)
results/                   report.md, metrics.json, timelines.json, failures_*.md, events/*.jsonl
intent.md evidence.md directive.md   Quest documents
```

## Data and safety

- All speech is synthetic (Microsoft edge-tts neural voices). No person was recorded.
- No API keys, no cloud APIs at run time. edge-tts is only used once to build the test data.
- Uploaded files on the review page are processed in memory and not stored by the app (Gradio keeps a
  temporary copy in its cache folder).
