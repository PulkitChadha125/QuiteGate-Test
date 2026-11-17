"""Held-out test set (data/holdout/), written AFTER v2 was frozen (see results/v2_freeze.txt).

Everything spoken here is new (no sentence is shared with the dev set), and it adds the situations the dev set
did not test:
  - more Korean calls and stops (callers and stoppers are drawn 50/50 Korean/English);
  - near-misses aimed at v2's own rules: "Stop by my desk..." (stop as 1st word), "그만큼..." (starts like 그만),
    "Travis said..." (sounds like Jarvis), "자비스라는 업체" (name mention without 씨);
  - mid-sentence pauses inside a call ("cuts sentences in half"): label turn_pauses;
  - people talking while the assistant answers (false stops): label talk_during_reply;
  - 3 calls per scene with calls, so about 50 calls and 35 stops.
"""
import json
import random

import numpy as np
import soundfile as sf

from .scenarios import SR, VOICES, REPLY_TEXT, DATA, _pink_noise, load_tts, make_reply, synth_all

HOLDOUT = DATA / "holdout"

CHATTER = {
    "en": [
        "Can we push the client demo to Thursday?",
        "The service desk got forty tickets yesterday.",
        "Jarvis is also the name of our new vendor.",
        "Please don't stop the pilot before the review.",
        "Stop by my desk after lunch if you can.",
        "I'll send the summary to everyone tonight.",
        "Our churn went down two percent last month.",
        "Who is taking notes today?",
        "I think we need one more designer on the team.",
        "Let's park that topic for the next meeting.",
        "The contract renewal is due at the end of the month.",
        "Hey everyone, sorry I'm a bit late.",
        "Travis said the numbers look fine.",
        "Can someone share their screen?",
    ],
    "ko": [
        "고객 데모를 목요일로 미룰 수 있을까요?",
        "서비스 데스크에 어제 문의가 사십 건 들어왔어요.",
        "자비스라는 이름의 업체도 있어요.",
        "파일럿은 검토 전까지 멈추지 말아 주세요.",
        "그만큼 시간이 더 필요할 것 같아요.",
        "오늘 회의록은 누가 작성하나요?",
        "지난달 이탈률이 이 퍼센트 줄었어요.",
        "디자이너가 한 명 더 필요해 보여요.",
        "그 주제는 다음 회의 때 다시 이야기하죠.",
        "계약 갱신은 이번 달 말까지입니다.",
        "다들 늦어서 죄송합니다.",
        "화면 공유 좀 해 주실 수 있나요?",
    ],
}

CALLS = {
    "en": ["Hey Jarvis, can you list the action items?",
           "Hey Jarvis, who is presenting next?",
           "Hey Jarvis, remind us about the deadline."],
    "ko": ["헤이 자비스, 회의록 요약해 줘.", "헤이 자비스, 다음 발표자가 누구야?", "헤이 자비스, 마감일 알려 줘."],
    "ko_multi": ["Hey Jarvis, 회의록 요약해 줘.", "Hey Jarvis, 다음 발표자가 누구야?"],
}
# Calls with a mid-sentence pause: (first part, second part).
SPLIT_CALLS = {
    "en": [("Hey Jarvis, can you check", "the budget for next month?"),
           ("Hey Jarvis, what did we decide", "about the launch?")],
    "ko": [("헤이 자비스, 다음 주", "일정 좀 알려 줘."), ("헤이 자비스, 아까 결정한 거", "정리해 줘.")],
    "ko_multi": [("Hey Jarvis, 다음 주", "일정 좀 알려 줘.")],
}
STOPS = {"en": ["Stop.", "Stop, please.", "Okay, stop.", "Jarvis, stop."],
         "ko": ["그만.", "그만해요.", "멈춰.", "멈춰요.", "잠깐, 그만."]}
BACKCHANNEL = {"en": ["Okay, got it.", "Right, that makes sense.", "Good, thanks."],
               "ko": ["네, 알겠어요.", "그렇죠.", "좋네요.", "맞아요."]}


def _pool(spk, table):
    return table["ko_multi"] if spk["voice"].endswith("MultilingualNeural") and "ko_multi" in table \
        else table[spk["lang"]]


def plan(idx, rng, reply_s):
    kind = ["no_call", "call", "call_stop", "call_stop"][idx % 4]
    n_spk = rng.randint(4, 6)
    n_ko = rng.randint(2, min(3, n_spk - 2))
    speakers = ([("en", v) for v in rng.sample(VOICES["en"], n_spk - n_ko)] +
                [("ko", v) for v in rng.sample(VOICES["ko"], n_ko)])
    rng.shuffle(speakers)
    speakers = [{"id": f"S{i+1}", "lang": l, "voice": v, "gain_db": round(rng.uniform(-12, 0), 1)}
                for i, (l, v) in enumerate(speakers)]
    by_lang = {l: [s for s in speakers if s["lang"] == l] for l in ("en", "ko")}

    def pick(lang_first=None, exclude=None):
        lang = lang_first or ("ko" if rng.random() < 0.5 else "en")
        cand = [s for s in by_lang[lang] if s is not exclude] or [s for s in speakers if s is not exclude]
        return rng.choice(cand)

    items = []
    n_calls = 0 if kind == "no_call" else 3
    chat_between = [rng.randint(3, 5) for _ in range(n_calls + 1)]
    last = None
    for ci in range(n_calls + 1):
        for _ in range(chat_between[ci]):
            spk = rng.choice([s for s in speakers if s is not last])
            last = spk
            overlap = rng.random() < 0.15
            items.append({"kind": "chat", "spk": spk, "text": rng.choice(CHATTER[spk["lang"]]),
                          "gap": rng.uniform(-0.8, -0.3) if overlap else rng.uniform(0.3, 1.2)})
        if ci == n_calls:
            break
        spk = pick()
        last = spk
        it = {"kind": "call", "spk": spk, "gap": 0.0,
              "after": "stop" if kind == "call_stop" else "reply"}
        if rng.random() < 0.35:
            a, b = rng.choice(_pool(spk, SPLIT_CALLS))
            it.update(text=a, text2=b, pause=rng.uniform(0.4, 1.2))
        else:
            it["text"] = rng.choice(_pool(spk, CALLS))
        if it["after"] == "stop":
            it["stopper"] = pick()
            it["stop_text"] = rng.choice(STOPS[it["stopper"]["lang"]])
            it["stop_offset"] = rng.uniform(1.5, 3.0)
        elif rng.random() < 0.8:
            other = pick(exclude=spk)
            pool = BACKCHANNEL[other["lang"]] if rng.random() < 0.5 else CHATTER[other["lang"]]
            it.update(talker=other, talk_text=rng.choice(pool), talk_offset=rng.uniform(1.0, 3.5))
        items.append(it)
    return {"idx": idx, "kind": kind, "speakers": speakers, "items": items}


def pairs(p):
    out = []
    for it in p["items"]:
        out.append((it["text"], it["spk"]["voice"]))
        if "text2" in it:
            out.append((it["text2"], it["spk"]["voice"]))
        if "stop_text" in it:
            out.append((it["stop_text"], it["stopper"]["voice"]))
        if "talk_text" in it:
            out.append((it["talk_text"], it["talker"]["voice"]))
    return out


def layout(p, reply_s, rng_np):
    segs, speech, calls, stops, pauses, talk = [], [], [], [], [], []

    def put(start, text, spk):
        a = load_tts(text, spk["voice"])
        segs.append((start, a, spk["gain_db"]))
        end = start + len(a) / SR
        speech.append([round(start, 3), round(end, 3), spk["id"], spk["lang"], text])
        return end

    t = 0.8
    for it in p["items"]:
        start = max(0.3, t)
        end = put(start, it["text"], it["spk"])
        if it["kind"] == "chat":
            t = end + it["gap"]
            continue
        if "text2" in it:
            s2 = end + it["pause"]
            pauses.append([round(end, 3), round(s2, 3)])
            end = put(s2, it["text2"], it["spk"])
        calls.append({"start": round(start, 3), "end": round(end, 3), "lang": it["spk"]["lang"],
                      "speaker": it["spk"]["id"], "text": it["text"] + (" ... " + it["text2"] if "text2" in it else "")})
        expected_reply = end + 0.9
        if it["after"] == "stop":
            s_start = expected_reply + it["stop_offset"]
            s_end = put(s_start, it["stop_text"], it["stopper"])
            stops.append({"start": round(s_start, 3), "end": round(s_end, 3), "lang": it["stopper"]["lang"],
                          "speaker": it["stopper"]["id"], "text": it["stop_text"]})
            t = s_end + 1.5
        else:
            if "talk_text" in it:
                ts = expected_reply + it["talk_offset"]
                te = put(ts, it["talk_text"], it["talker"])
                talk.append([round(ts, 3), round(te, 3), it["talk_text"]])
            t = expected_reply + reply_s + 1.0
    duration = t + 1.0
    n = int(duration * SR)
    mix = np.zeros(n, dtype=np.float32)
    for start, a, gdb in segs:
        i = int(start * SR)
        seg = a[: max(0, n - i)] * 0.5 * (10 ** (gdb / 20))
        mix[i:i + len(seg)] += seg
    mix += 0.003 * _pink_noise(n, rng_np).astype(np.float32)
    mix = np.clip(mix, -0.99, 0.99)
    speech.sort(key=lambda s: s[0])
    label = {"id": f"holdout_{p['idx']:02d}", "kind": p["kind"], "split": "holdout", "duration": round(duration, 3),
             "speakers": [{k: s[k] for k in ("id", "lang", "voice", "gain_db")} for s in p["speakers"]],
             "speech": speech, "calls": calls, "stops": stops, "turn_pauses": pauses, "talk_during_reply": talk}
    return mix, label


def make_holdout(cfg):
    seed, n = cfg["eval"]["holdout_seed"], cfg["eval"]["holdout_n_scenes"]
    reply_s = make_reply()
    rng = random.Random(seed)
    plans = [plan(i, rng, reply_s) for i in range(n)]
    synth_all([pr for p in plans for pr in pairs(p)])
    (HOLDOUT / "scenes").mkdir(parents=True, exist_ok=True)
    labels = []
    for p in plans:
        mix, lab = layout(p, reply_s, np.random.default_rng(seed + p["idx"]))
        sf.write(HOLDOUT / "scenes" / f"{lab['id']}.flac", mix, SR, subtype="PCM_16")
        labels.append(lab)
    meta = {"seed": seed, "sample_rate": SR, "reply_s": round(reply_s, 3), "reply_text": REPLY_TEXT,
            "scenes": labels}
    (HOLDOUT / "labels.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta
