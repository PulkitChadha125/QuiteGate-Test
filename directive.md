# directive.md: instructions given to the AI tools

**Tool:** Claude Code (Claude Opus 5.5), run in the project folder on Windows 11, Python 3.11.7.

**To repeat the process:** put `QuietGate_Architecture_Plan.md` and the Quest brief (`raw requirements .md`) in an
empty folder, open Claude Code there, and give the messages below in order. I am responsible for checking the
output. Every number was checked by running the evaluation, not by reading the AI's summary.

## Standing rules (from the architecture plan, §11)

1. Python 3.10+, Windows and Linux. Minimal dependencies (numpy, soundfile, onnxruntime, openwakeword, vosk, edge-tts,
   pyyaml, sounddevice, pytest, gradio). No torch, no cloud APIs, no API keys.
2. openWakeWord with the ONNX runtime (tflite is not available on Windows).
3. Gate and metrics first, with unit tests; the gate must never start while someone is speaking.
4. All thresholds in config files, no magic numbers. Fixed seeds.
5. Report on data that was not used for tuning. Do not invent results; if a metric fails, say FAIL and why.
6. After each phase, run the tests and the evaluation and show the output.

## Prompts, in order

1. *"Analyze the files in my development folder, and then tell me in layman's terms … what exactly the client wants
   and how we are planning to do that. … Go through [the architecture plan]. Draw the requirements. … What is the
   minimal thing that we can do? We are going to host it on a server on a certain port …"*
   The AI flagged that browsers block the microphone on plain `http://ip:port`, so the hosted page uses recorded
   meetings and uploads, and the live-mic demo runs locally.
2. *"Can we develop this in Python?"* Yes, with Gradio for the review page.
3. *"Please start with the development and once done do the testing and show me results."* This built v1.
4. *"Create a readme.md … requirements.txt … run_project.bat …"*
5. *"Do thorough testing for this project …"* and *"change the running port to 6000"*. This covered the clean
   install, reruns, upload edge cases and the live-loop replay. The port became 6060, because browsers block 6000.
6. *"Create a .gitignore …"* and *"create a progress.md …"*
7. *"Please check our project thoroughly and tell me does it do all the things mentioned in the requirement."*
   This found the gaps: an inaccurate header in intent.md, no list of the alternatives checked, no time log, the
   untested "cuts sentences in half", and no seat breakdown.
8. *"It is specially written that it should work in Korean and it is not working … can we do code changes to fix
   this?"* The AI probed three Korean detection methods on single phrases. It then flagged that its best probe
   result was invalid because it used words from the test sentences, and proposed a frozen v2 plus a fresh held-out set.
9. *"Implement code changes and make sure all the things mentioned in this [brief] are completed."* This built v2
   on the dev set, froze it (`results/v2_freeze.txt`), built the held-out set, evaluated once, and updated all documents.

## Where AI output was checked or corrected

| # | What the AI produced | How it was caught | Correction |
|---|---|---|---|
| 1 | Vosk KO grammar without a garbage path | single-phrase probe: stop fired on every Korean sentence | free recognition (v1) |
| 2 | Gate ignored a new wake while ARMED | dev trace (scene_02): a false wake swallowed the real call | re-arm on a new wake + unit test |
| 3 | Stop honoured while ARMED | dev: wake score 1.00 but call missed; "so far" heard as "stop" | stop only acts while speaking |
| 4 | Korean mention filter by word position | re-evaluation: false wakes unchanged | honorific rule (자비스 + 씨) + unit test |
| 5 | Tangled scene-planning loop | code review before the first data run | rewritten |
| 6 | Review page allowed serving the whole project folder | code review | only `dist/` copies are served |
| 7 | intent.md header said "written before building" | requirement check | reworded: the test was fixed in the plan before building; the file was compiled from it |
| 8 | Best Korean probe (12/12 calls, 9/9 stops) used vocabulary taken from the test sentences | AI self-review before reporting | discarded; general vocabulary + new held-out set |
| 9 | v2 draft required "헤이 자비스" | dev scene_25: overlap swallowed "헤이", call missed | dropped |
| 10 | v2 vocabulary lacked 씨, so the honorific rule could never fire | dev: 23 false wakes from "자비스 씨가…" | added honorific words |
| 11 | Upload errors exposed a server path; per-block detection lists; model reloaded per upload | edge-case upload tests | fixed |
| 12 | Port 6000 | Chrome showed an error page while curl got HTTP 200 | default 6060 |
| 13 | Gradio sent usage analytics by default | requirement check | disabled |

**What I would check by hand:** listen to a few held-out meetings on the review page, rerun `python -m pytest -q` and
`python -m quietgate.cli eval`, and confirm that `results/report.md` matches the tables in `evidence.md` and `README.md`.
