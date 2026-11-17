Quest: Quiet Until Called
Objective

The customer is a team of 4 to 6 people who meet across Korean and English and share one AI speaker on the table. Their problem is control: AI voice assistants talk over people, cut sentences in half, and miss voices from one side of the table. The company that buys the speaker pays to get its meeting time and decisions back. The team will accept the speaker only if, in a real meeting, it stays quiet until someone calls it by name, stops at once when told to, and hears every person at the table. This is a fictional case built for this Quest. It is not a live MUST product test, and you do not need any MUST data or hardware. Task: Pick ONE track that matches your strength and build the smallest thing that proves you moved the customer's acceptance test. Voice AI track: build a gate that decides when the assistant may speak. It answers only when called by name, never during someone else's turn, and stops speaking when told to. Hardware track: build or configure an audio capture setup on any microphone or board you own, and show how well it picks up 4 to 6 seat positions around a table. Design track: design the desk-mode control, meaning how a first-time user knows the speaker is listening or quiet, how they call it and how they stop it, and test it with at least 3 people who have not seen it before. Task: Before you build, write down the acceptance test you are using as numbers, for example uncalled interruptions per 10 minutes, missed calls, seconds to stop after "stop", share of seats heard correctly, or share of first-time users who could call and stop it without help. Measure your work against those numbers before and after, and say plainly what still fails. Task: Check what already exists before you build (open wake-word, voice-activity and turn-detection models, voice APIs, existing libraries or designs) and say what you reused and what gap you built. Building from scratch what a public tool already does is not a plus.

Format

Real-work task, 4 hours maximum of work. Cut scope rather than stretch time.
Submit within 48 hours of receiving the Quest.
Suggested 4-hour plan: Hour 1, write the acceptance test as numbers and check what already exists. Hours 2-3, build the smallest thing that moves it and measure before and after. Hour 4, write evidence.md and record the Loom.
The Quest is unpaid. Keep to 4 hours; cut scope rather than stretch time. The only paid stage is Quest 2, the 3-day paid test that comes later in the process.
Use only synthetic or public data: your own recordings made with the consent of everyone recorded, synthetic speech, or a public meeting dataset such as the AMI Meeting Corpus. Never use confidential data from an employer or client.
Before you start, we agree in writing: IP, confidentiality, how you may use AI and that you are responsible for checking its output, that we will not commercially use work from candidates we do not hire, and whether your work may be published (only with your consent).
Scoring: Problem understanding 25, Customer value 35, Verification & evidence 25, Collaboration & explanation 15 (total 100).
Pass: 80/100 or more AND no critical verification or security defect. A critical defect (numbers that cannot be reproduced, recordings of people without consent, exposed API keys) fails the Quest whatever the score.
Two assessors score independently; a gap of more than 15 points goes to evidence review. You get a decision, or a note saying when to expect one, within 48 hours of submission.
Submit everything in MatchHire.
Deliverables
Working deliverable link

one public link a customer could open and review. Voice track: your runnable project. Hardware track: a short clip plus wiring or config notes and the measurements. Design track: a clickable prototype plus the notes from your user tests.

intent.md

the customer's problem in your own words, the acceptance test you chose as numbers, the track you picked and why, and what you decided to leave out to fit 4 hours.

Final directive.md

the instructions you gave your AI tools, written so another person could repeat your process, and where you checked or corrected what they gave you.

evidence.md

the acceptance test you used, how you verified it, the before-and-after numbers, what you reused, where AI helped and where you corrected it, and what still fails.

Loom video

at most 5 minutes, explaining it as you would to the customer and the team, showing the thing working, not only slides.

How your submission is evaluated
Problem understanding (25): You state the customer's problem and acceptance test in your own words, as numbers, before building, and you pick a scope that fits 4 hours.

Customer value (35): What you built moves the acceptance test a real meeting team cares about (fewer uncalled interruptions, fewer missed calls, faster stop, more seats heard, or first-time users who can call and stop it), reusing what exists and building only the gap, not features or polish.

Verification & evidence (25): Before-and-after numbers a reviewer can repeat, what you reused versus built, where AI output was checked or corrected, and what still fails, stated plainly.

Collaboration & explanation (15): The Loom and evidence.md explain the work in plain words to the customer and the team, show it working, and name the next test.

Ready to start?
When you accept, your timer starts and you can upload files and add links. Declining withdraws you from the process.