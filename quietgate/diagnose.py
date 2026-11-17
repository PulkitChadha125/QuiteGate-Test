"""Explain every failure of one system on one data set. Writes results/<set>/failures_<system>.md.

python -m quietgate.diagnose [--set holdout|dev] [--system quietgate_v2|quietgate_v1|baseline] [--split ...]
"""
import argparse
import json
import sys
from collections import Counter

from .config import load_config
from .run_eval import RESULTS, V1_CONFIG, load_labels, load_signals


def _near(lab, t, pad=0.6):
    seg = [s for s in lab["speech"] if s[0] - 0.3 <= t <= s[1] + pad]
    return seg[-1] if seg else None


def diagnose(set_name="holdout", system="quietgate_v2", split=None):
    cfg = load_config(V1_CONFIG) if system == "quietgate_v1" else load_config()
    labels = load_labels(set_name)
    tl = json.loads((RESULTS / set_name / "timelines.json").read_text())
    ev, tg = cfg["eval"], cfg["targets"]
    out, causes = [], Counter()
    for lab in labels["scenes"]:
        if split and lab["split"] != split:
            continue
        rows = load_signals(set_name, lab["id"], cfg)
        spk = {s["id"]: s for s in lab["speakers"]}
        iv = tl[lab["id"]][system]

        def who(sid):
            s = spk.get(sid, {})
            return f"{s.get('voice', '?')} ({s.get('gain_db', '?')} dB)"
        for c in lab["calls"]:
            if any(c["start"] <= a[0] <= c["end"] + ev["missed_call_window_s"] for a in iv):
                continue
            w = [r for r in rows if c["start"] - 0.2 <= r["t"] <= c["end"] + 1.0]
            heard = any(r["wake_oww"] or r["wake_ko"] for r in w)
            pause = any(c["start"] < p[0] < c["end"] for p in lab.get("turn_pauses", []))
            if not heard:
                why = "wake word not detected"
            elif any(a[0] < c["start"] < a[1] for a in iv):
                why = "assistant was already talking (an earlier wrong start)"
            else:
                why = "wake detected, but no 700 ms silence within 8 s (overlapping talk)"
            causes[f"missed call: {why}"] += 1
            out.append(f"| {lab['id']} | missed call | \"{c['text']}\" | {who(c['speaker'])} | {why}"
                       f"{' (call had a mid-sentence pause)' if pause else ''} |")
        for a in iv:
            t = a[0]
            if any(c["start"] <= t and t - c["end"] <= ev["uncalled_window_s"] for c in lab["calls"]):
                if any(p[0] < t < p[1] for p in lab.get("turn_pauses", [])):
                    causes["started inside caller's mid-sentence pause"] += 1
                    out.append(f"| {lab['id']} | cut a sentence in half at {t}s | (call with a pause) | | "
                               f"pause longer than the 700 ms end-of-turn rule |")
                continue
            wk = [r for r in rows if t - 10 < r["t"] <= t and (r["wake_oww"] or r["wake_ko"])]
            src = "openWakeWord" if wk and wk[-1]["wake_oww"] else "Vosk-KO 자비스" if wk else "?"
            s = _near(lab, wk[-1]["t"]) if wk else None
            causes[f"uncalled start: false wake from {src}"] += 1
            out.append(f"| {lab['id']} | uncalled start at {t}s | \"{s[4] if s else '?'}\" | "
                       f"{who(s[2]) if s else '?'} | false wake ({src}) at {wk[-1]['t'] if wk else '?'}s |")
        for a in iv:
            if any(s[0] < a[0] < s[1] for s in lab["speech"]):
                s = next(s for s in lab["speech"] if s[0] < a[0] < s[1])
                causes["talk-over start"] += 1
                out.append(f"| {lab['id']} | talk-over start at {a[0]}s | \"{s[4]}\" | {who(s[2])} | "
                           f"someone started talking just as the assistant began |")
            if a[2] == "stop" and not any(st["start"] - 0.2 <= a[1] <= st["end"] + ev["stop_miss_s"]
                                          for st in lab["stops"]):
                s = _near(lab, a[1])
                causes["false stop (reply cut, nobody said stop)"] += 1
                out.append(f"| {lab['id']} | false stop at {a[1]}s | \"{s[4] if s else '?'}\" | "
                           f"{who(s[2]) if s else '?'} | stop detector fired on ordinary talk |")
        for st in lab["stops"]:
            a = next((a for a in iv if a[0] <= st["start"] < a[1]), None)
            if a is None:
                continue
            lat = a[1] - st["end"]
            if lat <= tg["stop_latency_p95_s"]:
                continue
            det = [r["t"] for r in rows if st["start"] <= r["t"] <= st["end"] + 2 and r["stop"]]
            why = (f"detected late at {det[0]}s" if det else "stop word not recognised")
            causes[f"slow/missed stop: {why.split(' at ')[0]}"] += 1
            out.append(f"| {lab['id']} | slow/missed stop ({lat:.2f}s) | \"{st['text']}\" | {who(st['speaker'])} | {why} |")
    head = [f"# Failure list: {system} on the {set_name} set" + (f" ({split} split)" if split else ""), "",
            "## Causes, counted", ""] + [f"- {n} x {k}" for k, n in causes.most_common()] + \
           ["", "## Every failure", "", "| Scene | Failure | What was said | Voice (seat gain) | Why |",
            "|---|---|---|---|---|"]
    text = "\n".join(head + (out or ["| - | none | | | |"])) + "\n"
    (RESULTS / set_name).mkdir(parents=True, exist_ok=True)
    (RESULTS / set_name / f"failures_{system}.md").write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="holdout")
    ap.add_argument("--system", default="quietgate_v2")
    ap.add_argument("--split", default=None)
    a = ap.parse_args()
    print(diagnose(a.set, a.system, a.split))
