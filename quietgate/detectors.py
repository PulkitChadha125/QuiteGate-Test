"""Thin wrappers around REUSED open-source detectors. Each takes one 80 ms int16 block (1280 samples @ 16 kHz).

- VadDetector:   Silero VAD (ONNX, the copy bundled with openWakeWord)
- WakeDetector:  openWakeWord pre-trained "hey_jarvis" model (ONNX)
- WordDetector:  Vosk small models.
    EN: grammar restricted to ["stop", "[unk]"]  -> stop word
    KO: free recognition (the small KO model has no [unk] token, so a grammar would force every
        sound into a stop word). We scan partial results for stop words (그만, 멈춰) and for the
        Korean pronunciation of the wake name (자비스), which openWakeWord misses.
"""
import json
import os

import numpy as np

from .config import ROOT


class VadDetector:
    def __init__(self, threshold=0.5, hangover_ms=240, block_ms=80):
        from openwakeword.vad import VAD
        self.vad = VAD()
        self.threshold = threshold
        self.hang_blocks = int(round(hangover_ms / block_ms))
        self._hang = 0
        self.last_prob = 0.0

    def process(self, block: np.ndarray) -> bool:
        self.last_prob = float(self.vad.predict(block, frame_size=640))
        if self.last_prob >= self.threshold:
            self._hang = self.hang_blocks
            return True
        if self._hang > 0:
            self._hang -= 1
            return True
        return False


class WakeDetector:
    def __init__(self, model="hey_jarvis", threshold=0.5):
        from openwakeword.model import Model
        self.model = Model(wakeword_models=[model], inference_framework="onnx")
        self.key = next(iter(self.model.models.keys()))
        self.threshold = threshold
        self.last_score = 0.0

    def process(self, block: np.ndarray) -> bool:
        self.last_score = float(self.model.predict(block)[self.key])
        return self.last_score >= self.threshold


class _TokenCounter:
    """Counts matching tokens in a growing Vosk partial result, so each spoken word fires once.

    Optional rules (all off by default):
    reject_next  (v1) skip a match followed by a token with one of these prefixes. Korean honorific 씨:
                 "자비스 씨가 ..." talks ABOUT someone; "헤이 자비스, ..." CALLS the assistant. A match that is
                 the last token of a partial waits for the next token (or the end of the utterance).
    require_prev (v2) the match only counts right after this exact token: the call form "헤이 자비스".
    max_index    (v2) the match only counts as one of the first max_index+1 words of the utterance.
                 Commands are short ("stop", "okay stop", "그만", "잠깐 그만"); a stop-like word at the
                 end of a long sentence ("... 먼저 멈춰", "we should stop spending") is ordinary talk.
    """

    def __init__(self, prefixes, reject_next=(), require_prev=None, max_index=None):
        self.prefixes = tuple(prefixes)
        self.reject_next = tuple(reject_next or ())
        self.require_prev = require_prev
        self.max_index = max_index
        self.seen = 0

    def _count(self, toks, final):
        n = 0
        for i, tok in enumerate(toks):
            if not tok.startswith(self.prefixes):
                continue
            if self.max_index is not None and i > self.max_index:
                continue
            if self.require_prev is not None and (i == 0 or toks[i - 1] != self.require_prev):
                continue
            if self.reject_next:
                if i + 1 < len(toks):
                    if toks[i + 1].startswith(self.reject_next):
                        continue
                elif not final:
                    continue
            n += 1
        return n

    def update(self, text, final):
        n = self._count(text.split(), final)
        fired = n > self.seen
        self.seen = 0 if final else max(self.seen, n)
        return fired


def load_vocab(path):
    """Read config/ko_vocab.txt: whitespace-separated words, '#' starts a comment."""
    full = path if os.path.isabs(path) else str(ROOT / path)
    words = []
    with open(full, encoding="utf-8") as f:
        for line in f:
            words += line.split("#", 1)[0].split()
    return list(dict.fromkeys(words))


_VOSK_MODELS = {}


def _vosk_model(p):
    """Load each Vosk model once per process (the KO model is 250 MB; recognisers are cheap)."""
    from vosk import Model
    full = p if os.path.isabs(p) else str(ROOT / p)
    if full not in _VOSK_MODELS:
        _VOSK_MODELS[full] = Model(full)
    return _VOSK_MODELS[full]


class WordDetector:
    """Returns (stop, wake_ko) per block."""

    def __init__(self, cfg, sample_rate=16000):
        from vosk import KaldiRecognizer, SetLogLevel
        SetLogLevel(-1)
        st, wk = cfg["stop"], cfg["wake"]
        max_index = st.get("max_index")
        self.en = KaldiRecognizer(_vosk_model(st["model_en"]), sample_rate,
                                  json.dumps(list(st["words_en"]) + ["[unk]"]))
        if st.get("ko_mode", "free") == "grammar":
            # v2: Korean keywords + a general vocabulary as the "everything else" path
            # (the small KO model has no [unk] token, so the vocabulary plays that role).
            words = list(st["ko_keywords"]) + [w for w in load_vocab(st["ko_vocab"]) if w not in st["ko_keywords"]]
            self.ko = KaldiRecognizer(_vosk_model(st["model_ko"]), sample_rate, json.dumps(words, ensure_ascii=False))
        else:
            self.ko = KaldiRecognizer(_vosk_model(st["model_ko"]), sample_rate)
        self.en_stop = _TokenCounter(st["words_en"], max_index=max_index)
        self.ko_stop = _TokenCounter(st["words_ko"], max_index=max_index)
        self.ko_wake = _TokenCounter(wk["words_ko"], reject_next=wk.get("ko_reject_next", ()),
                                     require_prev=wk.get("ko_require_prev"))

    @staticmethod
    def _feed(rec, data):
        if rec.AcceptWaveform(data):
            return json.loads(rec.Result()).get("text", ""), True
        return json.loads(rec.PartialResult()).get("partial", ""), False

    def process(self, block: np.ndarray):
        data = block.astype(np.int16).tobytes()
        en_text, en_final = self._feed(self.en, data)
        ko_text, ko_final = self._feed(self.ko, data)
        stop = self.en_stop.update(en_text, en_final) | self.ko_stop.update(ko_text, ko_final)
        wake_ko = self.ko_wake.update(ko_text, ko_final)
        return stop, wake_ko


def build_detectors(cfg):
    return (VadDetector(cfg["vad"]["threshold"], cfg["vad"]["hangover_ms"], cfg["block_ms"]),
            WakeDetector(cfg["wake"]["model"], cfg["wake"]["threshold"]),
            WordDetector(cfg, cfg["sample_rate"]))


def detect_stream(blocks, cfg):
    """Run all detectors over an iterable of blocks. Returns raw per-block signal rows (cached by eval)."""
    vad, wake, words = build_detectors(cfg)
    bs = cfg["sample_rate"] * cfg["block_ms"] // 1000
    rows = []
    for i, b in enumerate(blocks):
        sp = vad.process(b)
        wk = wake.process(b)
        stop, wake_ko = words.process(b)
        rows.append({"t": round((i + 1) * bs / cfg["sample_rate"], 3), "speech": sp,
                     "wake_oww": wk, "wake_ko": wake_ko, "stop": stop,
                     "p_speech": round(vad.last_prob, 3), "p_wake": round(wake.last_score, 3)})
    return rows
