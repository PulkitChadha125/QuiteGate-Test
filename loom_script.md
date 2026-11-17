# Loom script (5 minutes or less)

Record with headphones on. Have three things open: the review page (`http://localhost:6060`), a terminal in the
project folder, and `evidence.md`.

## 0:00 to 0:40: the problem (talk to the customer)
"Your team meets in Korean and English around one speaker. Today it jumps in at every pause, talks over people,
and won't stop when told. You told us you'd accept it only if it stays quiet until someone calls it by name, never
talks over anyone, and stops at once. I turned that into six numbers *before* building." Show the target column of
the Results tab.

## 0:40 to 1:10: what I reused vs built
"I didn't build speech models. Wake word: openWakeWord. Voice activity: Silero. Stop words and Korean: Vosk. All
free, offline, no API keys. What I built is the gate that combines them, plus a fair test against a naive assistant."

## 1:10 to 2:40: show it working, live
Terminal: `.venv\Scripts\python.exe -m quietgate.cli live`
1. Talk normally for 5 seconds, then pause. "Nothing happens. It stays quiet."
2. "Hey Jarvis, what's on the agenda?" and pause. Point at `ARMED`, then `STARTS speaking` about 0.7 s after you stop.
3. While it talks, say "stop". Point at `STOPPED`.
4. Say "Jarvis said the report is ready". Nothing happens (no "hey").
5. Optional: "헤이 자비스, 오늘 안건이 뭐야?" then "그만".

## 2:40 to 3:30: before vs after
Review page, tab 2, pick a held-out meeting with calls and a stop (e.g. `holdout_02`). Play the left player (naive:
talks at every pause, ignores stop), then the right player (QuietGate v2). Then tab 1, held-out table:
"Uncalled interruptions dropped from 20 to about 4 per 10 minutes, missed calls from 26 % to 11 %, and it now obeys
'stop' 29 times out of 33, usually within a tenth of a second. Korean calls missed went from 24 % in my first version
to 7 %."

## 3:30 to 4:30: what still fails (say it plainly)
"It does **not** pass your test yet; on new sentences only the reply-delay target passes.
- It still wakes up when people *mention* the name, like 'a company called Jarvis'. That is most of the false interruptions.
- If someone pauses longer than 0.7 seconds mid-sentence, it can jump in.
- About 1 in 8 stop commands are missed or slightly slow, mostly one Korean voice.
And this is synthetic speech. Real rooms will be harder."

## 4:30 to 5:00: next test
"Next: record a real meeting with 4 to 6 consenting people, train a custom wake word for '헤이 자비스' so name mentions
stop triggering it, and replace the fixed pause rule with a learned end-of-turn model. Then rerun the same six
numbers on a new held-out set." End.
