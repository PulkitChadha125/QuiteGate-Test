"""Synthetic meeting scenes with ground-truth labels (no real people recorded).

Speech comes from Microsoft edge-tts neural voices (en-US and ko-KR). Each scene mixes 3-5 speakers
taking turns with short pauses and some overlaps, at different gains (0 to -12 dB, near/far seats)
plus low pink noise. Labels come from the generator, not from any detector, so they are ground truth.

Scene types (index % 3): 0 = no-call chatter, 1 = call(s), 2 = call(s) followed by a stop command.
"""
import asyncio
import hashlib
import io
import json
import random

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from .config import ROOT

SR = 16000
DATA = ROOT / "data"
CACHE = DATA / "tts_cache"
SCENES = DATA / "scenes"
REPLY_WAV = ROOT / "assets" / "reply_en.wav"

VOICES = {
    "en": ["en-US-GuyNeural", "en-US-JennyNeural", "en-US-AriaNeural", "en-US-AndrewNeural", "en-US-EmmaNeural"],
    "ko": ["ko-KR-SunHiNeural", "ko-KR-InJoonNeural", "ko-KR-HyunsuMultilingualNeural"],
}

CHATTER = {
    "en": [
        "Let's look at the budget numbers for next quarter.",
        "I think the launch date should move by one week.",
        "Jarvis said the report would be ready on Friday.",          # near-miss: name without "hey"
        "Our customer service team needs two more people.",            # near-miss: "service"
        "Can you share the slides after the meeting?",
        "The jars in the lab were labeled incorrectly.",               # near-miss: "jars"
        "We should stop spending so much on paid ads.",                # "stop" in normal talk
        "Hey, did everyone get the calendar invite?",                  # near-miss: "hey"
        "I agree, but the design review has to come first.",
        "The Seoul office will join the call at three.",
        "Let me check the numbers and get back to you.",
        "The marketing plan looks good to me.",
        "Who owns the follow up on hiring?",
        "Okay, moving on to the next item on the list.",
        "That's a fair point, let's write it down as a decision.",
        "Honestly, I am not sure the vendor can deliver on time.",
    ],
    "ko": [
        "다음 분기 예산을 먼저 보죠.",
        "출시 일정은 일주일 미루는 게 좋겠어요.",
        "고객 서비스 팀에 두 명이 더 필요합니다.",
        "회의 끝나고 자료 공유해 주세요.",
        "서울 사무실은 세 시에 합류합니다.",
        "디자인 검토가 먼저인 것 같아요.",
        "그 부분은 제가 확인해 보겠습니다.",
        "좋아요, 다음 안건으로 넘어가죠.",
        "채용 후속 조치는 누가 맡나요?",
        "마케팅 계획은 괜찮아 보입니다.",
        "자비스 씨가 보고서를 금요일에 준다고 했어요.",                    # near-miss: name in a sentence
        "광고비 지출은 좀 줄여야 할 것 같아요.",
    ],
}

CALLS = {
    "en": ["Hey Jarvis, what is on the agenda today?",
           "Hey Jarvis, summarize the decisions so far.",
           "Hey Jarvis, how much time do we have left?"],
    # Korean speakers: the multilingual voice says the English phrase, the others say it the Korean way.
    "ko_multi": ["Hey Jarvis, 오늘 안건이 뭐야?", "Hey Jarvis, 지금까지 결정 사항 정리해 줘."],
    "ko": ["헤이 자비스, 오늘 안건이 뭐야?", "헤이 자비스, 남은 시간이 얼마야?"],
}

STOPS = {"en": ["Stop.", "Okay, stop."], "ko": ["그만.", "멈춰.", "그만해."]}

REPLY_TEXT = ("Here is the agenda. First, the budget review. Second, the launch timeline. "
              "Third, hiring for the Seoul office.")


# ---------------------------------------------------------------- TTS with cache
def _key(text, voice):
    return hashlib.sha1(f"{voice}|{text}".encode("utf-8")).hexdigest()[:16]


async def _tts_one(text, voice, sem):
    import edge_tts
    path = CACHE / f"{_key(text, voice)}.wav"
    if path.exists():
        return
    async with sem:
        for attempt in range(4):
            try:
                buf = b""
                async for ch in edge_tts.Communicate(text, voice).stream():
                    if ch["type"] == "audio":
                        buf += ch["data"]
                a, sr = sf.read(io.BytesIO(buf), dtype="float32")
                if a.ndim > 1:
                    a = a.mean(axis=1)
                if sr != SR:
                    g = np.gcd(sr, SR)
                    a = resample_poly(a, SR // g, sr // g)
                sf.write(path, _trim(a), SR, subtype="PCM_16")
                return
            except Exception:
                if attempt == 3:
                    raise
                await asyncio.sleep(1 + attempt)


def _trim(a, rel=0.02):
    """Trim leading/trailing silence so ground-truth speech intervals are tight."""
    frame = 160
    n = len(a) // frame
    if n == 0:
        return a
    rms = np.sqrt((a[: n * frame].reshape(n, frame) ** 2).mean(axis=1))
    on = np.where(rms > rms.max() * rel)[0]
    if len(on) == 0:
        return a
    return a[on[0] * frame: (on[-1] + 1) * frame]


def synth_all(pairs, concurrency=6):
    CACHE.mkdir(parents=True, exist_ok=True)

    async def main():
        sem = asyncio.Semaphore(concurrency)
        await asyncio.gather(*[_tts_one(t, v, sem) for t, v in set(pairs)])
    asyncio.run(main())


def load_tts(text, voice):
    a, _ = sf.read(CACHE / f"{_key(text, voice)}.wav", dtype="float32")
    return a


# ---------------------------------------------------------------- scene planning
def _pink_noise(n, rng):
    white = rng.standard_normal(n)
    f = np.fft.rfft(white)
    f /= np.sqrt(np.maximum(np.arange(len(f)), 1))
    p = np.fft.irfft(f, n)
    return p / (np.abs(p).max() + 1e-9)


def plan_scene(idx, rng: random.Random, reply_s):
    kind = ["no_call", "call", "call_stop"][idx % 3]
    n_spk = rng.randint(3, 5)
    n_ko = rng.randint(1, n_spk - 1)
    speakers = ([("en", v) for v in rng.sample(VOICES["en"], n_spk - n_ko)] +
                [("ko", v) for v in rng.sample(VOICES["ko"], min(n_ko, 3))])
    rng.shuffle(speakers)
    speakers = [{"id": f"S{i+1}", "lang": l, "voice": v, "gain_db": round(rng.uniform(-12, 0), 1)}
                for i, (l, v) in enumerate(speakers)]
    target = rng.uniform(60, 90)
    n_calls = 0 if kind == "no_call" else rng.randint(1, 2)
    call_marks = sorted(rng.uniform(0.2, 0.75) * target for _ in range(n_calls))
    if n_calls == 2 and call_marks[1] - call_marks[0] < 22:
        call_marks[1] = call_marks[0] + 22

    # Plan with estimated durations (about 3 s per sentence); layout_scene uses the real audio lengths.
    items, t, last, ci = [], 0.8, None, 0
    while t < target:
        spk = rng.choice([s for s in speakers if s is not last])
        last = spk
        if ci < len(call_marks) and t >= call_marks[ci]:
            ci += 1
            multi = spk["voice"].endswith("MultilingualNeural")
            pool = CALLS["ko_multi"] if multi else CALLS[spk["lang"]]
            it = {"kind": "call", "spk": spk, "text": rng.choice(pool),
                  "after": "stop" if kind == "call_stop" else "reply", "gap": 0.0}
            if it["after"] == "stop":
                it["stopper"] = rng.choice(speakers)
                it["stop_text"] = rng.choice(STOPS[it["stopper"]["lang"]])
                it["stop_offset"] = rng.uniform(1.5, 3.0)
                t += 3.0 + 0.9 + it["stop_offset"] + 2.5
            else:
                t += 3.0 + 0.9 + reply_s + 1.0
        else:
            overlap = rng.random() < 0.15
            it = {"kind": "chat", "spk": spk, "text": rng.choice(CHATTER[spk["lang"]]),
                  "gap": rng.uniform(-0.8, -0.3) if overlap else rng.uniform(0.3, 1.2)}
            t += 3.0 + it["gap"]
        items.append(it)
    return {"idx": idx, "kind": kind, "speakers": speakers, "items": items, "target": target}


def tts_pairs(plan):
    pairs = []
    for it in plan["items"]:
        pairs.append((it["text"], it["spk"]["voice"]))
        if "stop_text" in it:
            pairs.append((it["stop_text"], it["stopper"]["voice"]))
    return pairs


def layout_scene(plan, reply_s, rng_np):
    """Place utterances on the timeline using real audio lengths. Returns (mix, label)."""
    segs, speech, calls, stops = [], [], [], []
    t = 0.8
    for it in plan["items"]:
        a = load_tts(it["text"], it["spk"]["voice"])
        start = max(0.3, t)
        segs.append((start, a, it["spk"]["gain_db"]))
        end = start + len(a) / SR
        speech.append([round(start, 3), round(end, 3), it["spk"]["id"], it["spk"]["lang"], it["text"]])
        if it["kind"] == "call":
            calls.append({"start": round(start, 3), "end": round(end, 3), "lang": it["spk"]["lang"],
                          "speaker": it["spk"]["id"], "text": it["text"]})
            expected_reply = end + 0.9          # ~700 ms end-of-turn + VAD hangover
            if it["after"] == "stop":
                s_audio = load_tts(it["stop_text"], it["stopper"]["voice"])
                s_start = expected_reply + it["stop_offset"]
                s_end = s_start + len(s_audio) / SR
                segs.append((s_start, s_audio, it["stopper"]["gain_db"]))
                speech.append([round(s_start, 3), round(s_end, 3), it["stopper"]["id"], it["stopper"]["lang"], it["stop_text"]])
                stops.append({"start": round(s_start, 3), "end": round(s_end, 3),
                              "lang": it["stopper"]["lang"], "speaker": it["stopper"]["id"],
                              "text": it["stop_text"]})
                t = s_end + 1.5
            else:
                t = expected_reply + reply_s + 1.0   # the room waits while the assistant answers
        else:
            t = end + it["gap"]
    duration = t + 1.0
    n = int(duration * SR)
    mix = np.zeros(n, dtype=np.float32)
    for start, a, gdb in segs:
        i = int(start * SR)
        seg = a[: max(0, n - i)] * 0.5 * (10 ** (gdb / 20))
        mix[i:i + len(seg)] += seg
    mix += 0.003 * _pink_noise(n, rng_np).astype(np.float32)   # about -50 dBFS
    mix = np.clip(mix, -0.99, 0.99)
    speech.sort(key=lambda s: s[0])
    label = {"id": f"scene_{plan['idx']:02d}", "kind": plan["kind"], "duration": round(duration, 3),
             "speakers": [{k: s[k] for k in ("id", "lang", "voice", "gain_db")} for s in plan["speakers"]],
             "speech": speech, "calls": calls, "stops": stops}
    return mix, label


def make_reply():
    synth_all([(REPLY_TEXT, "en-US-AvaNeural")])
    a = load_tts(REPLY_TEXT, "en-US-AvaNeural")
    REPLY_WAV.parent.mkdir(parents=True, exist_ok=True)
    sf.write(REPLY_WAV, a, SR, subtype="PCM_16")
    return len(a) / SR


def make_data(cfg):
    seed, n, n_tune = cfg["eval"]["seed"], cfg["eval"]["n_scenes"], cfg["eval"]["n_tune"]
    reply_s = make_reply()
    rng = random.Random(seed)
    plans = []
    for i in range(n):
        plans.append(plan_scene(i, rng, reply_s))
    synth_all([pr for p in plans for pr in tts_pairs(p)])
    SCENES.mkdir(parents=True, exist_ok=True)
    labels = []
    for p in plans:
        mix, lab = layout_scene(p, reply_s, np.random.default_rng(seed + p["idx"]))
        lab["split"] = "tune" if p["idx"] < n_tune else "test"
        sf.write(SCENES / f"{lab['id']}.flac", mix, SR, subtype="PCM_16")
        labels.append(lab)
    meta = {"seed": seed, "sample_rate": SR, "reply_s": round(reply_s, 3), "reply_text": REPLY_TEXT,
            "scenes": labels}
    with open(DATA / "labels.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    return meta
