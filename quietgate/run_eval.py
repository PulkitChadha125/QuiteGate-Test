"""Run the baseline and QuietGate over every scene and write results/.

Detectors run once per scene and their per-block outputs are cached in data/signals/, so gate logic
can be re-evaluated in seconds. All gates see exactly the same detector outputs (fair comparison).
"""
import hashlib
import json
import platform
from concurrent.futures import ProcessPoolExecutor
from importlib.metadata import version

import numpy as np
import soundfile as sf

from .config import ROOT, load_config
from .detectors import detect_stream
from .gate import NaiveGate, Signals, TurnGate, simulate
from .metrics import METRIC_KEYS, aggregate, check_targets, scene_metrics

DATA = ROOT / "data"
RESULTS = ROOT / "results"
SIGNALS = DATA / "signals"


def _detector_key(cfg):
    sub = {k: cfg[k] for k in ("sample_rate", "block_ms", "vad", "wake", "stop")}
    return hashlib.sha1(json.dumps(sub, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:10]


def _blocks(path, block):
    a, sr = sf.read(path, dtype="int16")
    n = len(a) // block
    return [a[i * block:(i + 1) * block] for i in range(n)]


def _detect_scene(args):
    scene_id, cfg = args
    key = _detector_key(cfg)
    out = SIGNALS / f"{scene_id}.{key}.json"
    if out.exists():
        return scene_id
    block = cfg["sample_rate"] * cfg["block_ms"] // 1000
    rows = detect_stream(_blocks(DATA / "scenes" / f"{scene_id}.flac", block), cfg)
    out.write_text(json.dumps(rows))
    return scene_id


def detect_all(cfg, labels, workers=4):
    SIGNALS.mkdir(parents=True, exist_ok=True)
    todo = [(s["id"], cfg) for s in labels["scenes"]]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for sid in ex.map(_detect_scene, todo):
            print(f"  detectors done: {sid}", flush=True)


def load_signals(scene_id, cfg):
    return json.loads((SIGNALS / f"{scene_id}.{_detector_key(cfg)}.json").read_text())


def to_signals(rows, use_ko_wake):
    return [Signals(r["t"], r["speech"], r["wake_oww"] or (use_ko_wake and r["wake_ko"]), r["stop"])
            for r in rows]


def gate_factories(cfg):
    g, w = cfg["gate"], cfg["wake"]
    return {
        "baseline": (lambda: NaiveGate(cfg["baseline"]["end_of_turn_ms"]), False),
        "quietgate_oww_only": (lambda: TurnGate(g["end_of_turn_ms"], g["armed_timeout_s"], w["refractory_s"]), False),
        "quietgate": (lambda: TurnGate(g["end_of_turn_ms"], g["armed_timeout_s"], w["refractory_s"]),
                      bool(w.get("korean_vosk", True))),
    }


def evaluate(cfg, labels, reply_s):
    per_gate = {}
    timelines = {}
    for name, (make, use_ko) in gate_factories(cfg).items():
        rows_by_split = {"tune": [], "test": []}
        for lab in labels["scenes"]:
            sig = to_signals(load_signals(lab["id"], cfg), use_ko)
            gate = make()
            gate.name = name
            intervals, log = simulate(gate, sig, reply_s)
            m = scene_metrics(lab, intervals, cfg["eval"])
            rows_by_split[lab["split"]].append(m)
            timelines.setdefault(lab["id"], {})[name] = [[round(a, 3), round(b, 3), e] for a, b, e in intervals]
            ev_dir = RESULTS / "events" / name
            ev_dir.mkdir(parents=True, exist_ok=True)
            with open(ev_dir / f"{lab['id']}.jsonl", "w", encoding="utf-8") as f:
                for line in log:
                    f.write(json.dumps(line) + "\n")
        per_gate[name] = {split: aggregate(rows) for split, rows in rows_by_split.items()}
    return per_gate, timelines


def _versions():
    out = {"python": platform.python_version()}
    for pkg in ("openwakeword", "vosk", "onnxruntime", "numpy", "edge-tts"):
        try:
            out[pkg] = version(pkg)
        except Exception:
            out[pkg] = "?"
    return out


def _fmt(v):
    if v is None:
        return "n/a"
    return f"{v:g}" if isinstance(v, (int, float)) else str(v)


NICE = {"uncalled_per_10min": "Uncalled interruptions / 10 min",
        "talk_over_starts": "Talk-over starts",
        "missed_call_rate": "Missed calls (share)",
        "stop_latency_p95_s": "Stop latency p95 (s)",
        "stop_miss_rate": "Stop misses (share)",
        "reply_delay_median_s": "Reply delay after call, median (s)"}


def write_report(cfg, labels, per_gate, meta):
    t = cfg["targets"]
    lines = ["# QuietGate evaluation report", "",
             f"Test split: {meta['n_test']} scenes, {per_gate['baseline']['test']['minutes']} min of synthetic meeting audio "
             f"(seed {cfg['eval']['seed']}). Tune split ({meta['n_tune']} scenes) is reported separately below.", "",
             "## Acceptance test - test split (before vs after)", "",
             "| Metric | Target | Before: baseline | After: QuietGate | Pass? | QuietGate, openWakeWord only |",
             "|---|---|---|---|---|---|"]
    test = {k: v["test"] for k, v in per_gate.items()}
    chk = check_targets(test["quietgate"], t)
    for k in METRIC_KEYS:
        lines.append(f"| {NICE[k]} | <= {_fmt(t[k])} | {_fmt(test['baseline'][k])} | **{_fmt(test['quietgate'][k])}** | "
                     f"{'PASS' if chk[k][2] else 'FAIL'} | {_fmt(test['quietgate_oww_only'][k])} |")
    q = test["quietgate"]
    lines += ["", "## Detail (test split, QuietGate)", "",
              f"- Assistant starts: {q['assistant_starts']} (baseline: {test['baseline']['assistant_starts']})",
              f"- Wake calls: {q['calls']}, missed: {q['missed_calls']}; by language: "
              f"EN {_fmt(q['missed_call_rate_by_lang']['en']['value'])} of {q['missed_call_rate_by_lang']['en']['n']}, "
              f"KO {_fmt(q['missed_call_rate_by_lang']['ko']['value'])} of {q['missed_call_rate_by_lang']['ko']['n']}",
              f"- Stop commands measurable (assistant was talking): {q['stops_applicable']}; not measurable "
              f"(assistant had not started, e.g. missed call): {q['stops_not_applicable']}",
              f"- Stop misses by language: EN {_fmt(q['stop_miss_rate_by_lang']['en']['value'])} of "
              f"{q['stop_miss_rate_by_lang']['en']['n']}, KO {_fmt(q['stop_miss_rate_by_lang']['ko']['value'])} of "
              f"{q['stop_miss_rate_by_lang']['ko']['n']}",
              f"- Stop latency p50: {_fmt(q['stop_latency_p50_s'])} s", "",
              "## Tune split (used to choose thresholds; not the headline numbers)", "",
              "| Metric | Baseline | QuietGate |", "|---|---|---|"]
    for k in METRIC_KEYS:
        lines.append(f"| {NICE[k]} | {_fmt(per_gate['baseline']['tune'][k])} | {_fmt(per_gate['quietgate']['tune'][k])} |")
    lines += ["", "## Reproducibility", "",
              f"- Config hash: `{cfg['_hash']}`  labels.json sha1: `{meta['labels_sha1']}`",
              f"- Versions: " + ", ".join(f"{k} {v}" for k, v in meta["versions"].items()),
              "- Models: openWakeWord hey_jarvis_v0.1 (ONNX), Silero VAD (ONNX, bundled with openWakeWord), "
              "vosk-model-small-en-us-0.15, vosk-model-small-ko-0.22",
              "- Rerun: `python -m quietgate.cli eval`", ""]
    (RESULTS / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return "\n".join(lines)


def run(cfg_path=None, workers=4):
    cfg = load_config(cfg_path)
    lab_path = DATA / "labels.json"
    labels = json.loads(lab_path.read_text(encoding="utf-8"))
    print("Running detectors (cached after first run)...", flush=True)
    detect_all(cfg, labels, workers)
    RESULTS.mkdir(exist_ok=True)
    per_gate, timelines = evaluate(cfg, labels, labels["reply_s"])
    meta = {"n_tune": sum(s["split"] == "tune" for s in labels["scenes"]),
            "n_test": sum(s["split"] == "test" for s in labels["scenes"]),
            "labels_sha1": hashlib.sha1(lab_path.read_bytes()).hexdigest()[:12],
            "config_hash": cfg["_hash"], "versions": _versions()}
    (RESULTS / "metrics.json").write_text(json.dumps({"meta": meta, "targets": cfg["targets"], "gates": per_gate},
                                                     indent=1), encoding="utf-8")
    (RESULTS / "timelines.json").write_text(json.dumps(timelines), encoding="utf-8")
    return write_report(cfg, labels, per_gate, meta)
