# QuietGate evaluation report

Test split: 20 scenes, 22.27 min of synthetic meeting audio (seed 42). Tune split (10 scenes) is reported separately below.

## Acceptance test - test split (before vs after)

| Metric | Target | Before: baseline | After: QuietGate | Pass? | QuietGate, openWakeWord only |
|---|---|---|---|---|---|
| Uncalled interruptions / 10 min | <= 0.5 | 22.45 | **0.45** | PASS | 0 |
| Talk-over starts | <= 0 | 11 | **0** | PASS | 0 |
| Missed calls (share) | <= 0.1 | 0.167 | **0.111** | FAIL | 0.556 |
| Stop latency p95 (s) | <= 0.5 | 6.151 | **4.429** | FAIL | 5.277 |
| Stop misses (share) | <= 0.05 | 1 | **0.125** | FAIL | 0.2 |
| Reply delay after call, median (s) | <= 1.5 | 1.151 | **1.119** | PASS | 1.047 |

## Detail (test split, QuietGate)

- Assistant starts: 17 (baseline: 67)
- Wake calls: 18, missed: 2; by language: EN 0 of 8, KO 0.2 of 10
- Stop commands measurable (assistant was talking): 8; not measurable (assistant had not started, e.g. missed call): 1
- Stop misses by language: EN 0 of 3, KO 0.2 of 5
- Stop latency p50: 0.38 s

## Tune split (used to choose thresholds; not the headline numbers)

| Metric | Baseline | QuietGate |
|---|---|---|
| Uncalled interruptions / 10 min | 20.95 | 0.95 |
| Talk-over starts | 3 | 0 |
| Missed calls (share) | 0.2 | 0 |
| Stop latency p95 (s) | 5.761 | 3.942 |
| Stop misses (share) | 0.75 | 0.2 |
| Reply delay after call, median (s) | 1.154 | 1.122 |

## Reproducibility

- Config hash: `8382e9d64d05`  labels.json sha1: `b3d8ab10a4c7`
- Versions: python 3.11.7, openwakeword 0.6.0, vosk 0.3.45, onnxruntime 1.32.0, numpy 2.4.6, edge-tts 7.3.1
- Models: openWakeWord hey_jarvis_v0.1 (ONNX), Silero VAD (ONNX, bundled with openWakeWord), vosk-model-small-en-us-0.15, vosk-model-small-ko-0.22
- Rerun: `python -m quietgate.cli eval`
