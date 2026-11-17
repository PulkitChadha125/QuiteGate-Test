# directive.md: instructions given to the AI tools

Tool: Claude Code (Claude Opus 5.5), run in the project folder on Windows 11, Python 3.11.7.
Someone else can repeat the process by giving the same messages, in order, with `QuietGate_Architecture_Plan.md`
and `raw requirements .md` in the folder.

## Prompts, in order

1. *"Analyze the files in my development folder, and then tell me in layman's terms, in fewer words, what exactly
   the client wants and how we are planning to do that. I have created a QuietGate architecture plan also. Go
   through that also. Draw the requirements also. … What is the minimal thing that we can do? We are going to host
   it on a server on a certain port. Give that link to the client for checking, and also the raw files for him
   to review."*
   - The AI summarised the brief and reviewed the plan. It flagged that a browser blocks the microphone on plain
     `http://ip:port`, so the hosted page shows recorded scenes and uploads, and the live mic demo runs locally.
2. *"Can we develop this in Python?"* The answer was yes, with Gradio for the review page so everything stays in Python.
3. *"Sure please start with the development and once done do the testing and show me results."*
4. *"Create a readme.md file to explain what we have done in the project and how to use it. Create
   requirements.txt … create a run_project.bat file to install requirements and run the project."*
5. *"Do thorough testing for this project, and then get back to me if everything is working fine or not."* and
   *"Can we change the running port to 6000 …"* (changed to 6060 after showing that browsers block 6000).

The rules from section 11 of the architecture plan (minimal dependencies, ONNX for openWakeWord on Windows, gate
and metrics with unit tests first, all thresholds in config, fixed seed, tune/test split, no invented results)
applied throughout.

## Where AI output was checked or corrected

Every change was checked by running `pytest` and `quietgate eval` and reading the per-failure report
(`python -m quietgate.diagnose`). Corrections (details in `evidence.md` §6):

| # | What the AI produced | How it was caught | Correction |
|---|---|---|---|
| 1 | Vosk KO grammar for stop words | Single-phrase probe: stop fired on every Korean sentence | Free recognition + token matching |
| 2 | Gate ignored wake while ARMED | Tune-split trace of scene_02: false wake → real call missed | Re-arm on new wake + unit test |
| 3 | Stop honoured while ARMED | Tune split: wake 1.00 but call missed; trace showed "so far" → stop | Stop only acts while speaking |
| 4 | Korean mention filter by word position | Re-eval: false wakes unchanged | Honorific rule (자비스 + 씨) + unit test (disclosed as data-informed) |
| 5 | Tangled scene-planning loop | Code review before first data run | Rewritten |
| 6 | Review page initially allowed serving the whole project folder | Code review | Only `dist/` copies are served |
| 7 | Upload of a non-audio file showed a raw error with a server temp path | Edge-case upload tests | Friendly message |
| 8 | Wake/stop detections listed once per 80 ms block | Edge-case upload tests | One entry per spoken word |
| 9 | 250 MB Korean model reloaded on every upload | Timing of upload tests | Model cached per process |
| 10 | Requested port 6000 | Opened in Chrome: blocked (ERR_UNSAFE_PORT) although the server answered | Default port 6060 |

Human checks: listen to a few scenes on the review page, and confirm that the numbers in README/evidence match
`results/report.md` after a fresh `run_project.bat`.
