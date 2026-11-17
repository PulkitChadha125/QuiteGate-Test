# Failure list: quietgate_v1 on the holdout set

## Causes, counted

- 8 x missed call: wake word not detected
- 7 x slow/missed stop: stop word not recognised
- 7 x slow/missed stop: detected late
- 6 x started inside caller's mid-sentence pause
- 4 x uncalled start: false wake from Vosk-KO 자비스
- 4 x false stop (reply cut, nobody said stop)
- 1 x missed call: assistant was already talking (an earlier wrong start)

## Every failure

| Scene | Failure | What was said | Voice (seat gain) | Why |
|---|---|---|---|---|
| holdout_01 | missed call | "Hey Jarvis, 회의록 요약해 줘." | ko-KR-HyunsuMultilingualNeural (-6.9 dB) | wake word not detected |
| holdout_01 | uncalled start at 86.56s | "자비스라는 이름의 업체도 있어요." | ko-KR-HyunsuMultilingualNeural (-6.9 dB) | false wake (Vosk-KO 자비스) at 81.52s |
| holdout_01 | false stop at 88.24s | "계약 갱신은 이번 달 말까지입니다." | ko-KR-InJoonNeural (-1.3 dB) | stop detector fired on ordinary talk |
| holdout_02 | missed call | "헤이 자비스, 다음 주 ... 일정 좀 알려 줘." | ko-KR-SunHiNeural (-6.3 dB) | wake word not detected (call had a mid-sentence pause) |
| holdout_02 | missed call | "헤이 자비스, 다음 발표자가 누구야?" | ko-KR-SunHiNeural (-6.3 dB) | wake word not detected |
| holdout_02 | slow/missed stop (6.01s) | "그만해요." | ko-KR-SunHiNeural (-6.3 dB) | stop word not recognised |
| holdout_03 | slow/missed stop (5.81s) | "멈춰요." | ko-KR-SunHiNeural (-0.1 dB) | stop word not recognised |
| holdout_05 | cut a sentence in half at 36.64s | (call with a pause) | | pause longer than the 700 ms end-of-turn rule |
| holdout_05 | false stop at 62.8s | "좋네요." | ko-KR-SunHiNeural (-8.3 dB) | stop detector fired on ordinary talk |
| holdout_06 | cut a sentence in half at 15.28s | (call with a pause) | | pause longer than the 700 ms end-of-turn rule |
| holdout_06 | slow/missed stop (2.75s) | "그만해요." | ko-KR-HyunsuMultilingualNeural (-4.3 dB) | stop word not recognised |
| holdout_07 | cut a sentence in half at 62.0s | (call with a pause) | | pause longer than the 700 ms end-of-turn rule |
| holdout_07 | slow/missed stop (0.53s) | "멈춰." | ko-KR-InJoonNeural (-3.9 dB) | detected late at 67.84s |
| holdout_09 | missed call | "헤이 자비스, 마감일 알려 줘." | ko-KR-InJoonNeural (-5.8 dB) | wake word not detected |
| holdout_10 | missed call | "헤이 자비스, 다음 주 ... 일정 좀 알려 줘." | ko-KR-InJoonNeural (-6.7 dB) | wake word not detected (call had a mid-sentence pause) |
| holdout_10 | cut a sentence in half at 37.04s | (call with a pause) | | pause longer than the 700 ms end-of-turn rule |
| holdout_10 | cut a sentence in half at 54.56s | (call with a pause) | | pause longer than the 700 ms end-of-turn rule |
| holdout_10 | false stop at 44.08s | "자비스라는 이름의 업체도 있어요." | ko-KR-SunHiNeural (-7.0 dB) | stop detector fired on ordinary talk |
| holdout_10 | slow/missed stop (1.74s) | "멈춰요." | ko-KR-SunHiNeural (-7.0 dB) | detected late at 44.08s |
| holdout_10 | slow/missed stop (3.54s) | "멈춰요." | ko-KR-SunHiNeural (-7.0 dB) | stop word not recognised |
| holdout_11 | slow/missed stop (5.04s) | "그만." | ko-KR-SunHiNeural (-0.3 dB) | stop word not recognised |
| holdout_11 | slow/missed stop (5.56s) | "그만해요." | ko-KR-InJoonNeural (-8.5 dB) | stop word not recognised |
| holdout_13 | cut a sentence in half at 17.12s | (call with a pause) | | pause longer than the 700 ms end-of-turn rule |
| holdout_14 | missed call | "헤이 자비스, 다음 발표자가 누구야?" | ko-KR-SunHiNeural (-4.7 dB) | wake word not detected |
| holdout_14 | false stop at 26.08s | "Please don't stop the pilot before the review." | en-US-EmmaNeural (-6.3 dB) | stop detector fired on ordinary talk |
| holdout_14 | slow/missed stop (5.20s) | "그만해요." | ko-KR-SunHiNeural (-4.7 dB) | stop word not recognised |
| holdout_15 | slow/missed stop (0.53s) | "멈춰요." | ko-KR-InJoonNeural (-3.8 dB) | detected late at 58.48s |
| holdout_16 | uncalled start at 10.72s | "자비스라는 이름의 업체도 있어요." | ko-KR-HyunsuMultilingualNeural (-2.3 dB) | false wake (Vosk-KO 자비스) at 8.8s |
| holdout_18 | missed call | "Hey Jarvis, can you check ... the budget for next month?" | en-US-AndrewNeural (-0.4 dB) | assistant was already talking (an earlier wrong start) (call had a mid-sentence pause) |
| holdout_18 | uncalled start at 16.16s | "자비스라는 이름의 업체도 있어요." | ko-KR-HyunsuMultilingualNeural (-6.0 dB) | false wake (Vosk-KO 자비스) at 10.96s |
| holdout_18 | uncalled start at 73.6s | "Travis said the numbers look fine." | en-US-GuyNeural (-2.6 dB) | false wake (Vosk-KO 자비스) at 67.84s |
| holdout_18 | slow/missed stop (0.93s) | "그만." | ko-KR-InJoonNeural (-10.8 dB) | detected late at 25.36s |
| holdout_19 | slow/missed stop (0.56s) | "잠깐, 그만." | ko-KR-HyunsuMultilingualNeural (-0.7 dB) | detected late at 38.08s |
| holdout_22 | missed call | "헤이 자비스, 아까 결정한 거 ... 정리해 줘." | ko-KR-SunHiNeural (-1.5 dB) | wake word not detected (call had a mid-sentence pause) |
| holdout_22 | missed call | "Hey Jarvis, who is presenting next?" | en-US-GuyNeural (-10.1 dB) | wake word not detected |
| holdout_23 | slow/missed stop (0.52s) | "멈춰." | ko-KR-SunHiNeural (-9.0 dB) | detected late at 22.72s |
| holdout_23 | slow/missed stop (0.59s) | "멈춰요." | ko-KR-HyunsuMultilingualNeural (-3.1 dB) | detected late at 57.76s |
