"""Replay a test scene through the real live-mode loop (fake microphone, fake clock, fake speaker)
and check it starts/stops the assistant at the same moments as the offline evaluation.
Slow (loads models, ~20 s); skipped automatically when the models or the scene are missing."""
import json
import sys
import types

import numpy as np
import pytest
import soundfile as sf

from quietgate.config import ROOT, load_config

SCENE = ROOT / "data" / "scenes" / "scene_11.flac"
TIMELINES = ROOT / "results" / "dev" / "timelines.json"
needs = pytest.mark.skipif(not SCENE.exists() or not TIMELINES.exists() or not (ROOT / "models").exists(),
                           reason="needs data/, results/ (run eval) and models/")


@needs
def test_live_loop_matches_eval(monkeypatch, capsys):
    import quietgate.live as live
    cfg = load_config()
    block = cfg["sample_rate"] * cfg["block_ms"] // 1000
    audio, _ = sf.read(SCENE, dtype="int16")
    blocks = [audio[i * block:(i + 1) * block] for i in range(len(audio) // block)]
    clock = {"t": 0.0}
    events = []

    class FakeQueue:
        def __init__(self):
            self.i = 0

        def put(self, x):
            pass

        def get(self):
            if self.i >= len(blocks):
                raise KeyboardInterrupt
            b = blocks[self.i]
            self.i += 1
            clock["t"] = self.i * cfg["block_ms"] / 1000
            return b

    class FakeStream:
        def __init__(self, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_sd = types.SimpleNamespace(
        InputStream=FakeStream,
        play=lambda *a, **k: events.append(("start", clock["t"])),
        stop=lambda: events.append(("stop", clock["t"])))
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)
    monkeypatch.setattr(live, "queue", types.SimpleNamespace(Queue=FakeQueue))
    monkeypatch.setattr(live, "time", types.SimpleNamespace(time=lambda: clock["t"]))

    live.run_live(cfg)

    starts = [round(t, 2) for e, t in events if e == "start"]
    stops = [round(t, 2) for e, t in events[:-1] if e == "stop"]   # last stop = Ctrl+C cleanup
    tl = json.loads(TIMELINES.read_text())["scene_11"]["quietgate_v2"]   # live mode runs v2 (default config)
    assert starts == [round(a, 2) for a, _, _ in tl]
    assert stops == [round(b, 2) for _, b, how in tl if how == "stop"]
