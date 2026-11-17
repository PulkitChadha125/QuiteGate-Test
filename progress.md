# progress.md: QuietGate session log

**Last updated:** 17 Nov 2026 (evening)
**Status:** v2 built, frozen and evaluated on a new held-out set; all documents updated; review page running on
port 6060 locally. **Not yet:** time log filled in, git commit, server deployment, Loom.
**Resume at:** [Next steps](#next-steps-resume-here)

---

## What was done

### Day 1, part 1: v1 (see git history / directive.md prompts 1 to 6)
- Understood the brief; Voice AI track; Python + Gradio review page; port 6060 (browsers block 6000).
- Built the gate (IDLE → ARMED → SPEAKING), detectors (Silero VAD, openWakeWord, Vosk EN/KO), metrics, the dev set
  (30 meetings, seed 42), the evaluator, the failure explainer, the live mic demo, the review page, the tests,
  README, requirements.txt, run_project.bat and .gitignore.
- Thorough testing: clean install, reruns, upload edge cases, live-loop replay, Chrome. Several fixes.

### Day 1, part 2: requirement check → v2 → held-out evaluation
- **Requirement check** found gaps: an inaccurate intent.md header, no "what exists" list, no time log, "cuts
  sentences in half" untested, no seat breakdown, Gradio analytics on, Korean failing.
- **v2** (built on the dev set only): Korean via a Vosk grammar (keywords + general vocabulary `config/ko_vocab.txt`),
  a short-command rule for stop words (EN + KO), and the 씨 honorific rule for Korean mentions. Tried and dropped:
  requiring "헤이 자비스" (missed calls when speakers overlapped). v1 kept frozen in `config/v1.yaml`.
- **Froze v2** (`results/v2_freeze.txt`), *then* built a **held-out set** (`data/holdout/`, seed 2026): 24 meetings
  with new sentences, 54 calls (29 KO), 36 stops (20 KO), mid-sentence pauses, talk during replies, near-misses.
- **Evaluated once** on the held-out set, with no tuning after.

### Results: held-out set (the headline)
| Metric | Target | Naive | v1 | v2 | |
|---|---|---|---|---|---|
| Uncalled / 10 min | ≤ 0.5 | 20.34 | 1.66 | **4.15** | FAIL |
| Talk-over starts | 0 | 10 | 0 | **1** | FAIL |
| Missed calls | ≤ 10 % | 25.9 % | 16.7 % | **11.1 %** | FAIL |
| Stop p95 | ≤ 0.5 s | 6.05 | 5.70 | **5.38** (p50 0.11) | FAIL |
| Stop misses | ≤ 5 % | 90 % | 26.7 % | **12.1 %** | FAIL |
| Reply delay | ≤ 1.5 s | 1.08 | 1.07 | **1.08** | PASS |

Korean: missed calls 24.1 % → **6.9 %**, stop misses 44.4 % → **16.7 %** (v1 → v2).
On the dev set v2 passes all six, but that is optimistic (v2 was built while looking at dev).
**Main open failure:** false wakes on name *mentions* ("자비스라는 업체", "Jarvis is our vendor"); then 0.7 s
mid-sentence pauses, and a few missed or slow Korean stops.

### Files now
- Code: `quietgate/` (+ `holdout.py`), `app.py`, `config/default.yaml` (v2), `config/v1.yaml`, `config/ko_vocab.txt`
- Results: `results/report.md`, `results/holdout/` and `results/dev/` (metrics, timelines, failures, events), `results/v2_freeze.txt`
- Docs: `README.md`, `intent.md`, `evidence.md`, `directive.md`, `loom_script.md`, `progress.md`
- Tests: 17 passing

### Stress test (17 Nov, after v2)
- **Backend:** gate fuzzed with 3,000 random streams (≈ 99 h of audio, 40k starts): 0 starts during speech, 0 starts
  without a wake, 0 stops outside a reply, 0 crashes. Eval rerun reproduces `results/` byte for byte; v2 freeze hashes OK.
- **Frontend:** 300 page loads with 50 at once (p50 0.4 s); all 54 scenes render; 60 scene loads from 20 parallel users
  (≈ 6-7 s each; one viewer ≈ 1 s); bad scene ids rejected; project files not served (403/404); both zips download.
- **Uploads:** WAV/FLAC/OGG/MP3, 8-48 kHz, stereo, silence, 30 ms, noise, clipped, NaN, 5 min (capped at 3), empty,
  corrupt, text-as-wav: no crash, friendly errors. 6 parallel uploads give identical results (queued, ≈ 16 s each).
- **Fixed:** the source zip contained the whole `.git` folder (30 MB of history) → hidden folders excluded (now 0.3 MB);
  scene loads may run 4 at a time; upload tab now says to use 16 kHz+ WAV/FLAC.
- **Known limit:** 8 kHz phone audio lost 3 of 4 wake words, MP3 lost 1 of 4.

---

## Requirement check (after v2)

| Requirement | Status | Where |
|---|---|---|
| Pick one track | ✅ Voice AI | intent.md |
| Answers only when called by name | ⚠️ 5× fewer interruptions than naive, but 4.15 / 10 min on held-out (target 0.5); name mentions trigger it | evidence.md §4, §6 |
| Never during someone else's turn | ⚠️ 1 talk-over start on held-out (naive 10); cuts 5 of 25 mid-sentence pauses | evidence.md §5 |
| Stops when told | ⚠️ 29 of 33 stops obeyed (naive 3 of 30), typical 0.11 s; p95 and miss rate above target | evidence.md §4 |
| Korean and English | ✅ improved: KO missed calls 6.9 %, KO stop misses 16.7 % | evidence.md §4 |
| Acceptance test as numbers before building | ✅ plan §2; intent.md header now accurate | intent.md |
| Before and after, repeatable | ✅ naive vs v1 vs v2, shipped audio, frozen hashes, clean install tested | evidence.md §3 |
| Say plainly what still fails | ✅ | evidence.md §6, results/holdout/failures_quietgate_v2.md |
| Check what exists; reused vs built | ✅ options table added | evidence.md §2 |
| Synthetic data, no keys, no recordings of people | ✅ (analytics off) | |
| Public link to a runnable project | ⚠️ page ready on 6060, still needs hosting | app.py |
| intent.md / directive.md / evidence.md | ✅ updated (directive has 9 prompts + 13 corrections) | |
| Time log | ❌ must be filled in by Pulkit (evidence.md §8) | |
| Loom (5 minutes or less) | ❌ to record; script ready | loom_script.md |

---

## Next steps (resume here)

- [ ] Fill in the **real** time spent in `evidence.md` §8, and say whether v2 was done after the 4-hour mark
- [ ] Read `evidence.md` once end to end (it is what assessors score most)
- [ ] Decide whether `QuietGate_Architecture_Plan.md` and `raw requirements .md` go into a public repo
- [ ] `git add -A && git commit` (and push if you want a GitHub link too)
- [ ] Deploy: copy the folder to the server → `run_project.bat` → open TCP **6060** → test `http://<server-ip>:6060`
      from another network
- [ ] Try the live demo with headphones: `.venv\Scripts\python.exe -m quietgate.cli live`
- [ ] Record the Loom using `loom_script.md`
- [ ] Submit in MatchHire: link + intent.md + directive.md + evidence.md + Loom
- [ ] (Optional, a v3 for Quest 2) a custom openWakeWord model for "헤이 자비스" instead of the Korean ASR wake path,
      a learned end-of-turn model, then a **new** held-out set

## Quick commands
```
cd "D:\Desktop\python projects\QuietGate"
run_project.bat                                   :: setup + tests + eval + page on 6060
.venv\Scripts\python.exe app.py                   :: page only (port 6060)
.venv\Scripts\python.exe -m pytest -q             :: expect 17 passed
.venv\Scripts\python.exe -m quietgate.cli eval    :: naive vs v1 vs v2 on dev + held-out
.venv\Scripts\python.exe -m quietgate.diagnose    :: why each v2 held-out failure happened
.venv\Scripts\python.exe -m quietgate.cli live    :: live mic demo (headphones)
```
