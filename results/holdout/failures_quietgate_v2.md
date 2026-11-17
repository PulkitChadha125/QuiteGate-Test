# Failure list: quietgate_v2 on the holdout set

## Causes, counted

- 10 x uncalled start: false wake from Vosk-KO 자비스
- 5 x started inside caller's mid-sentence pause
- 4 x false stop (reply cut, nobody said stop)
- 4 x slow/missed stop: stop word not recognised
- 4 x slow/missed stop: detected late
- 3 x missed call: assistant was already talking (an earlier wrong start)
- 3 x missed call: wake word not detected
- 1 x talk-over start

## Every failure

| Scene | Failure | What was said | Voice (seat gain) | Why |
|---|---|---|---|---|
| holdout_01 | uncalled start at 56.4s | "자비스라는 이름의 업체도 있어요." | ko-KR-SunHiNeural (-1.6 dB) | false wake (Vosk-KO 자비스) at 54.4s |
| holdout_01 | uncalled start at 86.56s | "자비스라는 이름의 업체도 있어요." | ko-KR-HyunsuMultilingualNeural (-6.9 dB) | false wake (Vosk-KO 자비스) at 81.28s |
| holdout_01 | false stop at 88.24s | "계약 갱신은 이번 달 말까지입니다." | ko-KR-InJoonNeural (-1.3 dB) | stop detector fired on ordinary talk |
| holdout_02 | slow/missed stop (6.01s) | "그만해요." | ko-KR-SunHiNeural (-6.3 dB) | stop word not recognised |
| holdout_03 | slow/missed stop (0.63s) | "멈춰요." | ko-KR-SunHiNeural (-0.1 dB) | detected late at 37.36s |
| holdout_05 | cut a sentence in half at 36.64s | (call with a pause) | | pause longer than the 700 ms end-of-turn rule |
| holdout_05 | false stop at 62.8s | "좋네요." | ko-KR-SunHiNeural (-8.3 dB) | stop detector fired on ordinary talk |
| holdout_06 | cut a sentence in half at 15.28s | (call with a pause) | | pause longer than the 700 ms end-of-turn rule |
| holdout_06 | slow/missed stop (5.65s) | "Stop." | en-US-AndrewNeural (-5.3 dB) | stop word not recognised |
| holdout_07 | missed call | "Hey Jarvis, can you check ... the budget for next month?" | en-US-EmmaNeural (-7.6 dB) | assistant was already talking (an earlier wrong start) (call had a mid-sentence pause) |
| holdout_07 | uncalled start at 7.36s | "Jarvis is also the name of our new vendor." | en-US-JennyNeural (-10.4 dB) | false wake (Vosk-KO 자비스) at 5.92s |
| holdout_07 | uncalled start at 54.16s | "Jarvis is also the name of our new vendor." | en-US-JennyNeural (-10.4 dB) | false wake (Vosk-KO 자비스) at 46.96s |
| holdout_07 | talk-over start at 7.36s | "Travis said the numbers look fine." | en-US-EmmaNeural (-7.6 dB) | someone started talking just as the assistant began |
| holdout_09 | missed call | "헤이 자비스, 마감일 알려 줘." | ko-KR-InJoonNeural (-5.8 dB) | wake word not detected |
| holdout_10 | cut a sentence in half at 37.04s | (call with a pause) | | pause longer than the 700 ms end-of-turn rule |
| holdout_10 | cut a sentence in half at 54.56s | (call with a pause) | | pause longer than the 700 ms end-of-turn rule |
| holdout_10 | slow/missed stop (0.54s) | "멈춰요." | ko-KR-SunHiNeural (-7.0 dB) | detected late at 42.88s |
| holdout_10 | slow/missed stop (0.52s) | "멈춰요." | ko-KR-SunHiNeural (-7.0 dB) | detected late at 59.68s |
| holdout_11 | false stop at 26.08s | "Can someone share their screen?" | en-US-AndrewNeural (-0.1 dB) | stop detector fired on ordinary talk |
| holdout_11 | slow/missed stop (2.74s) | "그만." | ko-KR-SunHiNeural (-0.3 dB) | stop word not recognised |
| holdout_13 | missed call | "Hey Jarvis, can you check ... the budget for next month?" | en-US-GuyNeural (-3.0 dB) | assistant was already talking (an earlier wrong start) (call had a mid-sentence pause) |
| holdout_13 | cut a sentence in half at 17.12s | (call with a pause) | | pause longer than the 700 ms end-of-turn rule |
| holdout_13 | uncalled start at 60.64s | "The service desk got forty tickets yesterday." | en-US-GuyNeural (-3.0 dB) | false wake (Vosk-KO 자비스) at 55.12s |
| holdout_13 | uncalled start at 81.84s | "Hey everyone, sorry I'm a bit late." | en-US-JennyNeural (-7.6 dB) | false wake (Vosk-KO 자비스) at 78.4s |
| holdout_14 | false stop at 26.08s | "Please don't stop the pilot before the review." | en-US-EmmaNeural (-6.3 dB) | stop detector fired on ordinary talk |
| holdout_14 | slow/missed stop (5.20s) | "그만해요." | ko-KR-SunHiNeural (-4.7 dB) | stop word not recognised |
| holdout_16 | uncalled start at 10.72s | "자비스라는 이름의 업체도 있어요." | ko-KR-HyunsuMultilingualNeural (-2.3 dB) | false wake (Vosk-KO 자비스) at 8.56s |
| holdout_18 | missed call | "Hey Jarvis, can you check ... the budget for next month?" | en-US-AndrewNeural (-0.4 dB) | assistant was already talking (an earlier wrong start) (call had a mid-sentence pause) |
| holdout_18 | uncalled start at 16.16s | "자비스라는 이름의 업체도 있어요." | ko-KR-HyunsuMultilingualNeural (-6.0 dB) | false wake (Vosk-KO 자비스) at 10.96s |
| holdout_18 | uncalled start at 73.6s | "자비스라는 이름의 업체도 있어요." | ko-KR-HyunsuMultilingualNeural (-6.0 dB) | false wake (Vosk-KO 자비스) at 67.6s |
| holdout_19 | uncalled start at 68.0s | "Jarvis is also the name of our new vendor." | en-US-AndrewNeural (-7.7 dB) | false wake (Vosk-KO 자비스) at 62.08s |
| holdout_22 | missed call | "헤이 자비스, 아까 결정한 거 ... 정리해 줘." | ko-KR-SunHiNeural (-1.5 dB) | wake word not detected (call had a mid-sentence pause) |
| holdout_22 | missed call | "Hey Jarvis, who is presenting next?" | en-US-GuyNeural (-10.1 dB) | wake word not detected |
| holdout_23 | slow/missed stop (0.52s) | "멈춰." | ko-KR-SunHiNeural (-9.0 dB) | detected late at 22.72s |
