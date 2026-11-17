# QuietGate evaluation report

## Headline: held-out set (new sentences, built after v2 was frozen)

24 scenes, 24.09 min of synthetic meeting audio (seed 2026). Nothing was tuned on this set.

| Metric | Target | Before: naive assistant | QuietGate v1 | QuietGate v2 | v2 pass? |
|---|---|---|---|---|---|
| Uncalled interruptions / 10 min | <= 0.5 | 20.34 | 1.66 | **4.15** | FAIL |
| Talk-over starts | <= 0 | 10 | 0 | **1** | FAIL |
| Missed calls (share) | <= 0.1 | 0.259 | 0.167 | **0.111** | FAIL |
| Stop latency p95 (s) | <= 0.5 | 6.046 | 5.695 | **5.382** | FAIL |
| Stop misses (share) | <= 0.05 | 0.9 | 0.267 | **0.121** | FAIL |
| Reply delay after call, median (s) | <= 1.5 | 1.079 | 1.072 | **1.077** | PASS |

### Detail

**QuietGate v1**

- Assistant starts: 49 (uncalled: 4)
- Missed calls: 9 of 54. By language: EN 8.0 % of 25, KO 24.1 % of 29. By seat: near seats 14.8 % of 27, far seats 18.5 % of 27
- Stop commands measurable: 30 (not measurable, assistant not talking: 6). Misses by language: EN 0.0 % of 12, KO 44.4 % of 18. By seat: near seats 22.2 % of 18, far seats 33.3 % of 12
- Stop latency p50 0.453 s, p95 5.695 s
- *Cuts sentences in half:* assistant started inside a caller's mid-sentence pause 6 times (of 25 pauses)
- *False stops:* reply cut although nobody said stop: 4 times (people talked during 16 replies)

**QuietGate v2**

- Assistant starts: 58 (uncalled: 10)
- Missed calls: 6 of 54. By language: EN 16.0 % of 25, KO 6.9 % of 29. By seat: near seats 14.8 % of 27, far seats 7.4 % of 27
- Stop commands measurable: 33 (not measurable, assistant not talking: 3). Misses by language: EN 6.7 % of 15, KO 16.7 % of 18. By seat: near seats 15.0 % of 20, far seats 7.7 % of 13
- Stop latency p50 0.11 s, p95 5.382 s
- *Cuts sentences in half:* assistant started inside a caller's mid-sentence pause 5 times (of 25 pauses)
- *False stops:* reply cut although nobody said stop: 4 times (people talked during 16 replies)

**Naive assistant (before)**

- Assistant starts: 99 (uncalled: 49)
- Missed calls: 14 of 54. By language: EN 40.0 % of 25, KO 13.8 % of 29. By seat: near seats 25.9 % of 27, far seats 25.9 % of 27
- Stop commands measurable: 30 (not measurable, assistant not talking: 6). Misses by language: EN 84.6 % of 13, KO 94.1 % of 17. By seat: near seats 94.7 % of 19, far seats 81.8 % of 11
- Stop latency p50 5.191 s, p95 6.046 s
- *Cuts sentences in half:* assistant started inside a caller's mid-sentence pause 5 times (of 25 pauses)
- *False stops:* reply cut although nobody said stop: 0 times (people talked during 16 replies)

## Dev set, test split (scenes 10-29, seed 42)

v1's original headline set. Its failures were inspected while designing v2, so v2's numbers here are **optimistic** and are shown only for continuity.

| Metric | Target | Before: naive assistant | QuietGate v1 | QuietGate v2 | v2 pass? |
|---|---|---|---|---|---|
| Uncalled interruptions / 10 min | <= 0.5 | 22.45 | 0.45 | **0.45** | PASS |
| Talk-over starts | <= 0 | 11 | 0 | **0** | PASS |
| Missed calls (share) | <= 0.1 | 0.167 | 0.111 | **0.056** | PASS |
| Stop latency p95 (s) | <= 0.5 | 6.151 | 4.429 | **0.476** | PASS |
| Stop misses (share) | <= 0.05 | 1 | 0.125 | **0** | PASS |
| Reply delay after call, median (s) | <= 1.5 | 1.151 | 1.119 | **1.123** | PASS |

## Reproducibility

- Config hashes: v2 `85b4afde9998`, v1 `69a608b7006f`
- labels.json sha1: dev `b3d8ab10a4c7`, holdout `5252714e60ff`
- Versions: python 3.11.7, openwakeword 0.6.0, vosk 0.3.45, onnxruntime 1.32.0, numpy 2.4.6, edge-tts 7.3.1
- Models: openWakeWord hey_jarvis_v0.1 (ONNX), Silero VAD (ONNX, bundled with openWakeWord), vosk-model-small-en-us-0.15, vosk-model-small-ko-0.22; Korean grammar vocabulary config/ko_vocab.txt
- Rerun: `python -m quietgate.cli eval` (uses the shipped audio in data/ and data/holdout/)
