"""Explain every failure: missed calls, uncalled starts, missed/slow stops. Writes results/failures.md.

python -m quietgate.diagnose [--split test|tune|all]
"""
import argparse
import json
import sys

from .config import load_config
from .run_eval import DATA, RESULTS, load_signals


def diagnose(split="test", gate="quietgate"):
    cfg = load_config()
    labels = json.loads((DATA / "labels.json").read_text(encoding="utf-8"))
    tl = json.loads((RESULTS / "timelines.json").read_text())
    ev = cfg["eval"]
    out = []
    for lab in labels["scenes"]:
        if split != "all" and lab["split"] != split:
            continue
        rows = load_signals(lab["id"], cfg)
        spk = {s["id"]: s for s in lab["speakers"]}
        iv = tl[lab["id"]][gate]
        for c in lab["calls"]:
            if any(c["start"] <= a[0] <= c["end"] + ev["missed_call_window_s"] for a in iv):
                continue
            w = [r for r in rows if c["start"] - 0.2 <= r["t"] <= c["end"] + 1.0]
            s = spk[c["speaker"]]
            heard = any(r["wake_oww"] or r["wake_ko"] for r in w)
            why = ("wake word not detected" if not heard else
                   "wake detected but gate did not start (other speech / earlier state)")
            out.append(f"| {lab['id']} | missed call | \"{c['text']}\" | {s['voice']} ({s['gain_db']} dB) | "
                       f"max openWakeWord score {max(r['p_wake'] for r in w):.2f}; {why} |")
        for a in iv:
            if any(c["start"] <= a[0] and a[0] - c["end"] <= ev["uncalled_window_s"] for c in lab["calls"]):
                continue
            wk = [r for r in rows if a[0] - 10 < r["t"] <= a[0] and (r["wake_oww"] or r["wake_ko"])]
            src = ", ".join(f"{'openWakeWord' if r['wake_oww'] else 'Vosk-KO 자비스'} at {r['t']}s" for r in wk[:2])
            near = [s for s in lab["speech"] if wk and s[0] - 0.3 <= wk[0]["t"] <= s[1] + 0.6]
            txt = near[0][4] if near and len(near[0]) > 4 else "?"
            out.append(f"| {lab['id']} | uncalled start at {a[0]}s | \"{txt}\" | "
                       f"{spk[near[0][2]]['voice'] if near else '?'} | false wake: {src} |")
        for st in lab["stops"]:
            a = next((a for a in iv if a[0] <= st["start"] < a[1]), None)
            if a is None:
                continue
            lat = a[1] - st["end"]
            if lat <= cfg["targets"]["stop_latency_p95_s"]:
                continue
            det = [r["t"] for r in rows if st["start"] <= r["t"] <= st["end"] + 2 and r["stop"]]
            s = spk[st["speaker"]]
            out.append(f"| {lab['id']} | slow/missed stop ({lat:.2f}s) | \"{st['text']}\" | "
                       f"{s['voice']} ({s['gain_db']} dB) | "
                       f"{'stop word detected at ' + str(det[0]) + 's' if det else 'stop word not recognised by Vosk'} |")
    head = [f"# Failure list ({gate}, {split} split)", "",
            "| Scene | Failure | What was said | Voice (seat gain) | Why |", "|---|---|---|---|---|"]
    text = "\n".join(head + (out or ["| - | none | | | |"])) + "\n"
    (RESULTS / f"failures_{split}.md").write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    print(diagnose(ap.parse_args().split))
