"""Live microphone demo: say "Hey Jarvis, ..." then pause; say "stop" / "그만" while it talks.

Use headphones: there is no echo cancellation, so on laptop speakers the reply would be heard by the
microphone (it cannot trigger a wake or a stop by itself in most cases, but VAD will see it as speech).
"""
import queue
import time

import numpy as np
import soundfile as sf

from .detectors import build_detectors
from .gate import GateEvent, Signals, TurnGate
from .scenarios import REPLY_WAV


def run_live(cfg):
    import sounddevice as sd
    sr = cfg["sample_rate"]
    block = sr * cfg["block_ms"] // 1000
    reply, _ = sf.read(REPLY_WAV, dtype="float32")
    reply_s = len(reply) / sr
    vad, wake, words = build_detectors(cfg)
    g, w = cfg["gate"], cfg["wake"]
    gate = TurnGate(g["end_of_turn_ms"], g["armed_timeout_s"], w["refractory_s"])
    q = queue.Queue()

    def cb(indata, frames, t, status):
        q.put(indata[:, 0].copy())

    print("Listening. Say 'Hey Jarvis, what is on the agenda?' then pause. Say 'stop' / '그만' to cut it. Ctrl+C quits.")
    t0 = time.time()
    speaking_since = None
    last_state = gate.state
    with sd.InputStream(samplerate=sr, channels=1, dtype="int16", blocksize=block, callback=cb):
        try:
            while True:
                b = q.get()
                now = time.time() - t0
                sp = vad.process(b)
                wk = wake.process(b)
                stop, wake_ko = words.process(b)
                done = speaking_since is not None and now - speaking_since >= reply_s
                if done:
                    speaking_since = None
                for _, ev, _ in gate.step(Signals(now, sp, wk or (w.get("korean_vosk") and wake_ko), stop), done):
                    if ev == GateEvent.START:
                        sd.play(reply, sr)
                        speaking_since = now
                        print(f"[{now:7.2f}s] >>> assistant STARTS speaking")
                    elif ev == GateEvent.STOP:
                        sd.stop()
                        speaking_since = None
                        print(f"[{now:7.2f}s] ### assistant STOPPED (heard stop word)")
                if gate.state != last_state:
                    print(f"[{now:7.2f}s] state {last_state} -> {gate.state}")
                    last_state = gate.state
        except KeyboardInterrupt:
            sd.stop()
            print("bye")
