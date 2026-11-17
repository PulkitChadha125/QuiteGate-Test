"""QuietGate review page (Gradio). Run:  python app.py --port 6060   then open http://<server>:6060

Tabs: results (before vs after) / listen to a test scene with both gates / try your own audio / raw files.
"""
import argparse
import html
import json
import shutil
import sys
import zipfile
from pathlib import Path

import gradio as gr
import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from quietgate.config import load_config  # noqa: E402
from quietgate.gate import NaiveGate, TurnGate, simulate  # noqa: E402
from quietgate.run_eval import gate_factories, to_signals  # noqa: E402

CFG = load_config()
SR = CFG["sample_rate"]
DATA, RESULTS = ROOT / "data", ROOT / "results"
LABELS = json.loads((DATA / "labels.json").read_text(encoding="utf-8"))
SCENES = {s["id"]: s for s in LABELS["scenes"]}
TIMELINES = json.loads((RESULTS / "timelines.json").read_text())
REPLY, _ = sf.read(ROOT / "assets" / "reply_en.wav", dtype="float32")
REPLY_S = LABELS["reply_s"]
DIST = ROOT / "dist"

COL = {"en": "#4C78A8", "ko": "#9D6FD0", "baseline": "#D9534F", "quietgate": "#2E9E5B",
       "call": "#F0AD4E", "stop": "#333333"}
KIND = {"no_call": "meeting chatter, nobody calls the assistant",
        "call": "someone calls \"Hey Jarvis\"",
        "call_stop": "someone calls, then says stop while it answers"}


# ------------------------------------------------------------------ helpers
def timeline_svg(duration, speech, calls, stops, gates):
    """Simple SVG timeline: one row per speaker, call/stop markers, one row per gate."""
    W, left, rowh = 980, 130, 22
    spk_ids = sorted({s[2] for s in speech})
    rows = [(sid, [s for s in speech if s[2] == sid]) for sid in spk_ids]
    H = 30 + rowh * (len(rows) + len(gates) + 1) + 20
    x = lambda t: left + (W - left - 10) * t / max(duration, 1e-6)  # noqa: E731
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" '
           f'style="font-family:sans-serif;font-size:12px;background:#fff;border:1px solid #ddd;border-radius:6px">']
    for t in range(0, int(duration) + 1, 10):
        out.append(f'<line x1="{x(t):.1f}" y1="20" x2="{x(t):.1f}" y2="{H-20}" stroke="#eee"/>'
                   f'<text x="{x(t):.1f}" y="{H-6}" text-anchor="middle" fill="#888">{t}s</text>')
    y = 24
    for sid, segs in rows:
        lang = segs[0][3]
        out.append(f'<text x="6" y="{y+14}" fill="#333">{sid} ({lang.upper()})</text>')
        for s in segs:
            tip = html.escape(s[4]) if len(s) > 4 else ""
            out.append(f'<rect x="{x(s[0]):.1f}" y="{y+3}" width="{max(1, x(s[1])-x(s[0])):.1f}" height="{rowh-6}" '
                       f'fill="{COL[lang]}" rx="3"><title>{tip}</title></rect>')
        y += rowh
    for c in calls:
        out.append(f'<rect x="{x(c["start"]):.1f}" y="22" width="{max(2, x(c["end"])-x(c["start"])):.1f}" '
                   f'height="{rowh*len(rows)}" fill="{COL["call"]}" opacity="0.25"><title>call: {html.escape(c.get("text",""))}</title></rect>')
    for s in stops:
        out.append(f'<line x1="{x(s["end"]):.1f}" y1="22" x2="{x(s["end"]):.1f}" y2="{y + rowh*len(gates)}" '
                   f'stroke="{COL["stop"]}" stroke-dasharray="4 3"><title>stop: {html.escape(s.get("text",""))}</title></line>')
    y += 6
    for name, iv in gates:
        c = COL["baseline"] if name.startswith("baseline") else COL["quietgate"]
        out.append(f'<text x="6" y="{y+14}" fill="{c}" font-weight="bold">{html.escape(name)}</text>')
        for a, b, *_ in iv:
            out.append(f'<rect x="{x(a):.1f}" y="{y+3}" width="{max(1, x(b)-x(a)):.1f}" height="{rowh-6}" fill="{c}" rx="3">'
                       f'<title>assistant speaks {a:.2f}-{b:.2f}s</title></rect>')
        y += rowh
    out.append("</svg>")
    legend = ('<div style="font-size:12px;margin-top:4px">'
              f'<span style="color:{COL["en"]}">■</span> English speech &nbsp; <span style="color:{COL["ko"]}">■</span> Korean speech &nbsp; '
              f'<span style="color:{COL["call"]}">■</span> "Hey Jarvis" call &nbsp; ┆ stop command &nbsp; '
              f'<span style="color:{COL["baseline"]}">■</span> naive assistant talking &nbsp; '
              f'<span style="color:{COL["quietgate"]}">■</span> QuietGate assistant talking</div>')
    return "".join(out) + legend


def render_mix(audio, intervals):
    """Mix the assistant reply into the meeting audio where the gate let it speak (cut at STOP)."""
    out = audio.astype(np.float32).copy()
    for a, b, *_ in intervals:
        i, n = int(a * SR), int((b - a) * SR)
        seg = REPLY[:n] * 0.6
        seg = seg[: max(0, len(out) - i)]
        out[i:i + len(seg)] += seg
    return (SR, np.clip(out, -1, 1))


def count_line(lab, iv, cfg_eval):
    from quietgate.metrics import scene_metrics
    m = scene_metrics(lab, iv, cfg_eval)
    hit = sum(c["hit"] for c in m["calls"])
    st = [s for s in m["stops"] if s["applicable"]]
    s_txt = ", ".join(f'{s["latency"]:.2f}s' for s in st) or "-"
    return (f'{m["starts"]} times spoke, {m["uncalled"]} uncalled, {m["talk_over"]} talk-over starts, '
            f'answered {hit}/{len(m["calls"])} calls, stop latency: {s_txt}')


# ------------------------------------------------------------------ tab callbacks
def show_scene(scene_id):
    lab = SCENES[scene_id]
    audio, _ = sf.read(DATA / "scenes" / f"{scene_id}.flac", dtype="float32")
    tl = TIMELINES[scene_id]
    svg = timeline_svg(lab["duration"], lab["speech"], lab["calls"], lab["stops"],
                       [("baseline (before)", tl["baseline"]), ("QuietGate (after)", tl["quietgate"])])
    calls = "; ".join(f'"{c["text"]}" at {c["start"]:.1f}s' for c in lab["calls"]) or "none"
    stops = "; ".join(f'"{s["text"]}" at {s["start"]:.1f}s' for s in lab["stops"]) or "none"
    info = (f"**{scene_id}** ({lab['split']} split): {KIND[lab['kind']]}. {lab['duration']:.0f} s, "
            f"{len(lab['speakers'])} speakers.  \n**Calls:** {calls}  \n**Stops:** {stops}  \n"
            f"**Baseline:** {count_line(lab, tl['baseline'], CFG['eval'])}  \n"
            f"**QuietGate:** {count_line(lab, tl['quietgate'], CFG['eval'])}")
    return info, svg, render_mix(audio, tl["baseline"]), render_mix(audio, tl["quietgate"])


def analyse_upload(path):
    if not path:
        return "Upload a WAV/FLAC/MP3 file first.", "", None, None
    from scipy.signal import resample_poly
    from quietgate.detectors import detect_stream
    try:
        a, sr = sf.read(path, dtype="float32")
    except Exception:
        return ("Could not read this file as audio. Please upload a WAV, FLAC, OGG or MP3 file.",
                "", None, None)
    if len(a) == 0:
        return "The file contains no audio samples.", "", None, None
    if a.ndim > 1:
        a = a.mean(axis=1)
    if sr != SR:
        g = np.gcd(sr, SR)
        a = resample_poly(a, SR // g, sr // g).astype(np.float32)
    a = a[: SR * 180]   # cap at 3 minutes
    x = (np.clip(a, -1, 1) * 32767).astype(np.int16)
    block = SR * CFG["block_ms"] // 1000
    rows = detect_stream([x[i:i + block] for i in range(0, len(x) - block + 1, block)], CFG)
    res = {}
    for name, (make, use_ko) in gate_factories(CFG).items():
        if name == "quietgate_oww_only":
            continue
        res[name], _ = simulate(make(), to_signals(rows, use_ko), REPLY_S)
    # build pseudo speech rows from the VAD so the timeline has something to show
    speech, cur = [], None
    for r in rows:
        if r["speech"] and cur is None:
            cur = r["t"] - CFG["block_ms"] / 1000
        if not r["speech"] and cur is not None:
            speech.append([cur, r["t"], "VAD", "en"])
            cur = None
    if cur is not None:
        speech.append([cur, rows[-1]["t"], "VAD", "en"])
    dur = len(a) / SR

    def onsets(flag):
        """First block of each run of detections (one entry per spoken word, not per 80 ms block)."""
        out, prev = [], False
        for r in rows:
            cur = flag(r)
            if cur and not prev:
                out.append(r["t"])
            prev = cur
        return out
    wakes = onsets(lambda r: r["wake_oww"] or r["wake_ko"])
    stops = onsets(lambda r: r["stop"])
    svg = timeline_svg(dur, speech, [{"start": t - 0.3, "end": t, "text": "wake"} for t in wakes],
                       [{"start": t, "end": t, "text": "stop"} for t in stops],
                       [("baseline (before)", res["baseline"]), ("QuietGate (after)", res["quietgate"])])
    info = (f"{dur:.1f} s analysed. Wake detections at: {', '.join(f'{t:.2f}s' for t in wakes) or 'none'}. "
            f"Stop words at: {', '.join(f'{t:.2f}s' for t in stops) or 'none'}.  \n"
            f"Baseline spoke {len(res['baseline'])} times; QuietGate spoke {len(res['quietgate'])} times. "
            f"(Speech row = detected voice activity, not ground truth.)")
    return info, svg, render_mix(a, res["baseline"]), render_mix(a, res["quietgate"])


# ------------------------------------------------------------------ raw files
RAW = ["README.md", "intent.md", "evidence.md", "directive.md", "requirements.txt", "run_project.bat", "app.py",
       "config/default.yaml", "results/report.md", "results/metrics.json", "results/failures_test.md",
       "data/labels.json", "QuietGate_Architecture_Plan.md"]


def build_zips():
    DIST.mkdir(exist_ok=True)
    code_zip = DIST / "quietgate_source_and_results.zip"
    with zipfile.ZipFile(code_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for p in ROOT.rglob("*"):
            rel = p.relative_to(ROOT)
            if p.is_dir() or rel.parts[0] in {".venv", "models", "dist", ".gradio", ".pytest_cache"} \
                    or "__pycache__" in rel.parts or rel.parts[:2] in {("data", "tts_cache"), ("data", "signals"),
                                                                       ("data", "scenes")}:
                continue
            z.write(p, rel.as_posix())
    data_zip = DIST / "quietgate_test_audio.zip"
    if not data_zip.exists() or data_zip.stat().st_mtime < (DATA / "labels.json").stat().st_mtime:
        with zipfile.ZipFile(data_zip, "w", zipfile.ZIP_STORED) as z:
            for p in sorted((DATA / "scenes").glob("*.flac")):
                z.write(p, f"data/scenes/{p.name}")
            z.write(DATA / "labels.json", "data/labels.json")
    return [str(code_zip), str(data_zip)]


def raw_files():
    """Copy the reviewable files into dist/raw so only dist/ is ever served."""
    out_dir = DIST / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for f in RAW:
        src = ROOT / f
        if src.exists():
            dst = out_dir / f.replace("/", "__")
            shutil.copyfile(src, dst)
            out.append(str(dst))
    return out


def read_doc(name):
    p = ROOT / name
    return p.read_text(encoding="utf-8") if p.exists() else f"*{name} not found*"


# ------------------------------------------------------------------ UI
INTRO = """# QuietGate: an assistant that stays quiet until called

A meeting team of 4-6 people (Korean and English) shares one AI speaker. They reject it because it
**talks when nobody asked**, **talks over people**, and **won't stop when told**. QuietGate is a small layer
between the microphone and the assistant's voice that decides one thing: *may the assistant speak now?*

1. **Called by name only:** it stays silent until someone says "Hey Jarvis" (or 헤이 자비스).
2. **Never during someone's turn:** after the call it waits until the room is quiet (700 ms).
3. **Stops at once:** "stop", "그만" or "멈춰" cuts the reply.

All audio here is **synthetic** (Microsoft edge-tts voices). No real people were recorded.
"""


def build_ui():
    zips = build_zips()
    with gr.Blocks(title="QuietGate") as demo:
        gr.Markdown(INTRO)
        with gr.Tab("1. Results (before vs after)"):
            gr.Markdown(read_doc("results/report.md"))
        with gr.Tab("2. Listen to a test scene"):
            gr.Markdown("Pick a scene. The **red** player is a naive assistant that answers after any pause and "
                        "ignores stop. The **green** player is QuietGate. The assistant's reply is mixed in where each "
                        "one decided to talk. Hover over the bars to see what was said.")
            choices = [(f"{sid}: {KIND[s['kind']]} ({s['split']})", sid) for sid, s in SCENES.items()]
            dd = gr.Dropdown(choices=choices, value="scene_11", label="Scene")
            info = gr.Markdown()
            svg = gr.HTML()
            with gr.Row():
                a_base = gr.Audio(label="Before: naive assistant", type="numpy")
                a_qg = gr.Audio(label="After: QuietGate", type="numpy")
            dd.change(show_scene, dd, [info, svg, a_base, a_qg])
            demo.load(show_scene, dd, [info, svg, a_base, a_qg])
        with gr.Tab("3. Try your own audio"):
            gr.Markdown("Upload a recording (max 3 min; only upload audio you have consent to use). Say "
                        "\"Hey Jarvis, ...\", pause, and later \"stop\". Both gates run on it and you can listen to "
                        "where each one would have talked. Note: in a file the assistant is not really playing, so "
                        "say \"stop\" about 1-3 s after you finished your question.")
            up = gr.Audio(label="Your audio", type="filepath", sources=["upload"])
            btn = gr.Button("Analyse", variant="primary")
            info2 = gr.Markdown()
            svg2 = gr.HTML()
            with gr.Row():
                b_base = gr.Audio(label="Before: naive assistant", type="numpy")
                b_qg = gr.Audio(label="After: QuietGate", type="numpy")
            btn.click(analyse_upload, up, [info2, svg2, b_base, b_qg])
        with gr.Tab("4. Raw files"):
            gr.Markdown("Everything needed to review and rerun the work. `quietgate_source_and_results.zip` has the "
                        "code, config, docs and results; `quietgate_test_audio.zip` has the 30 synthetic test scenes "
                        "and their ground-truth labels.")
            gr.File(value=zips, label="Downloads", file_count="multiple", interactive=False)
            gr.File(value=raw_files(), label="Individual files", file_count="multiple", interactive=False)
        with gr.Tab("5. Docs"):
            for name in ("evidence.md", "intent.md", "README.md"):
                with gr.Accordion(name, open=name == "evidence.md"):
                    gr.Markdown(read_doc(name))
    return demo


def launch(host="0.0.0.0", port=6060):
    build_ui().launch(server_name=host, server_port=port, allowed_paths=[str(DIST)],
                      show_error=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=6060)
    a = ap.parse_args()
    launch(a.host, a.port)
