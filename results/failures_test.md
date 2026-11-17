# Failure list (quietgate, test split)

| Scene | Failure | What was said | Voice (seat gain) | Why |
|---|---|---|---|---|
| scene_13 | missed call | "헤이 자비스, 남은 시간이 얼마야?" | ko-KR-SunHiNeural (-5.7 dB) | max openWakeWord score 0.00; wake word not detected |
| scene_14 | missed call | "헤이 자비스, 남은 시간이 얼마야?" | ko-KR-InJoonNeural (-11.2 dB) | max openWakeWord score 0.00; wake word not detected |
| scene_17 | slow/missed stop (6.41s) | "그만해." | ko-KR-SunHiNeural (-2.0 dB) | stop word not recognised by Vosk |
| scene_17 | slow/missed stop (0.75s) | "그만." | ko-KR-HyunsuMultilingualNeural (-8.9 dB) | stop word detected at 44.08s |
| scene_26 | slow/missed stop (0.66s) | "멈춰." | ko-KR-SunHiNeural (-7.4 dB) | stop word detected at 40.96s |
| scene_29 | uncalled start at 58.72s | "자비스 씨가 보고서를 금요일에 준다고 했어요." | ko-KR-InJoonNeural | false wake: Vosk-KO 자비스 at 56.32s |
