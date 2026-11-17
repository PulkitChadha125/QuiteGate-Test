# Failure list (quietgate, tune split)

| Scene | Failure | What was said | Voice (seat gain) | Why |
|---|---|---|---|---|
| scene_02 | slow/missed stop (4.81s) | "그만해." | ko-KR-SunHiNeural (-11.3 dB) | stop word not recognised by Vosk |
| scene_06 | uncalled start at 14.24s | "자비스 씨가 보고서를 금요일에 준다고 했어요." | ko-KR-InJoonNeural | false wake: Vosk-KO 자비스 at 11.68s |
