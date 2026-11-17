"""Run the baseline, QuietGate v1 and QuietGate v2 over every scene of each data set and write results/.

Data sets
  dev      data/          30 scenes (seed 42). Used while building v1 and v2: tune split 0-9, test split 10-29.
  holdout  data/holdout/  24 scenes (seed 2026) with NEW sentences, built after v2 was frozen. Headline numbers.

Systems (each sees cached detector outputs, so all comparisons use the same audio and the same VAD):
  baseline      naive assistant: answers after any 700 ms pause, ignores "stop"
  quietgate_v1  config/v1.yaml  (first version, frozen)
  quietgate_v2  config/default.yaml (Korean grammar mode, short-command stop rule, "헤이 자비스" call form)
"""
import hashlib
import json
import platform
from concurrent.futures import ProcessPoolExecutor
from importlib.metadata import version

import soundfile as sf

from .config import ROOT, load_config
from .detectors import detect_stream
from .gate import NaiveGate, Signals, TurnGate, simulate
from .metrics import METRIC_KEYS, aggregate, check_targets, scene_metrics

DATA = ROOT / "data"
RESULTS = ROOT / "results"
SETS = {"dev": DATA, "holdout": DATA / "holdout"}
V1_CONFIG = ROOT / "config" / "v1.yaml"


def set_dir(name):
    return SETS[name]


def load_labels(name):
    return json.loads((set_dir(name) / "labels.json").read_text(encoding="utf-8"))


def _detector_key(cfg):
    sub = {k: cfg[k] for k in ("sample_rate", "block_ms", "vad", "wake", "stop")}
    if cfg["stop"].get("ko_vocab"):
        sub["_vocab"] = (ROOT / cfg["stop"]["ko_vocab"]).read_text(encoding="utf-8")
    return hashlib.sha1(json.dumps(sub, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:10]


def _blocks(path, block):
    a, _ = sf.read(path, dtype="int16")
    n = len(a) // block
    return [a[i * block:(i + 1) * block] for i in range(n)]


def _signal_path(set_name, scene_id, cfg):
    return set_dir(set_name) / "signals" / f"{scene_id}.{_detector_key(cfg)}.json"


def _detect_scene(args):
    set_name, scene_id, cfg = args
    out = _signal_path(set_name, scene_id, cfg)
    if out.exists():
        return scene_id
    block = cfg["sample_rate"] * cfg["block_ms"] // 1000
    rows = detect_stream(_blocks(set_dir(set_name) / "scenes" / f"{scene_id}.flac", block), cfg)
    out.write_text(json.dumps(rows))
    return scene_id


def detect_all(set_name, cfg, labels, workers=4):
    (set_dir(set_name) / "signals").mkdir(parents=True, exist_ok=True)
    todo = [(set_name, s["id"], cfg) for s in labels["scenes"]
            if not _signal_path(set_name, s["id"], cfg).exists()]
    if not todo:
        return
    print(f"  running detectors ({cfg.get('name', '?')}) on {len(todo)} {set_name} scenes ...", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for _ in ex.map(_detect_scene, todo):
            pass


def load_signals(set_name, scene_id, cfg):
    return json.loads(_signal_path(set_name, scene_id, cfg).read_text())


def to_signals(rows, use_ko_wake):
    return [Signals(r["t"], r["speech"], r["wake_oww"] or (use_ko_wake and r["wake_ko"]), r["stop"])
            for r in rows]


def systems(cfg_v2, cfg_v1):
    """name -> (gate factory, detector config whose cached outputs it reads, use Korean wake)."""
    def turn(cfg):
        g, w = cfg["gate"], cfg["wake"]
        return lambda: TurnGate(g["end_of_turn_ms"], g["armed_timeout_s"], w["refractory_s"])
    return {
        "baseline": (lambda: NaiveGate(cfg_v2["baseline"]["end_of_turn_ms"]), cfg_v2, False),
        "quietgate_v1": (turn(cfg_v1), cfg_v1, bool(cfg_v1["wake"].get("korean_vosk", True))),
        "quietgate_v2": (turn(cfg_v2), cfg_v2, bool(cfg_v2["wake"].get("korean_vosk", True))),
    }


def evaluate(set_name, labels, cfg_v2, cfg_v1):
    out_dir = RESULTS / set_name
    per_sys, timelines = {}, {}
    for name, (make, det_cfg, use_ko) in systems(cfg_v2, cfg_v1).items():
        by_split = {}
        for lab in labels["scenes"]:
            gate = make()
            gate.name = name
            intervals, log = simulate(gate, to_signals(load_signals(set_name, lab["id"], det_cfg), use_ko),
                                      labels["reply_s"])
            by_split.setdefault(lab["split"], []).append(scene_metrics(lab, intervals, cfg_v2["eval"]))
            timelines.setdefault(lab["id"], {})[name] = [[round(a, 3), round(b, 3), e] for a, b, e in intervals]
            ev_dir = out_dir / "events" / name
            ev_dir.mkdir(parents=True, exist_ok=True)
            with open(ev_dir / f"{lab['id']}.jsonl", "w", encoding="utf-8") as f:
                for line in log:
                    f.write(json.dumps(line) + "\n")
        per_sys[name] = {split: aggregate(rows) for split, rows in by_split.items()}
    return per_sys, timelines


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


def _pct(v):
    return "n/a" if v is None else f"{v * 100:.1f} %"


NICE = {"uncalled_per_10min": "Uncalled interruptions / 10 min",
        "talk_over_starts": "Talk-over starts",
        "missed_call_rate": "Missed calls (share)",
        "stop_latency_p95_s": "Stop latency p95 (s)",
        "stop_miss_rate": "Stop misses (share)",
        "reply_delay_median_s": "Reply delay after call, median (s)"}


def _table(agg_by_sys, targets, title_note=""):
    chk = check_targets(agg_by_sys["quietgate_v2"], targets)
    lines = ["| Metric | Target | Before: naive assistant | QuietGate v1 | QuietGate v2 | v2 pass? |",
             "|---|---|---|---|---|---|"]
    for k in METRIC_KEYS:
        lines.append(f"| {NICE[k]} | <= {_fmt(targets[k])} | {_fmt(agg_by_sys['baseline'][k])} | "
                     f"{_fmt(agg_by_sys['quietgate_v1'][k])} | **{_fmt(agg_by_sys['quietgate_v2'][k])}** | "
                     f"{'PASS' if chk[k][2] else 'FAIL'} |")
    return lines


def _detail(a, label):
    def lang(key):
        d = a[key]
        return f"EN {_pct(d['en']['value'])} of {d['en']['n']}, KO {_pct(d['ko']['value'])} of {d['ko']['n']}"

    def seat(key):
        d = a[key]
        return (f"near seats {_pct(d['near']['value'])} of {d['near']['n']}, "
                f"far seats {_pct(d['far']['value'])} of {d['far']['n']}")
    return [f"**{label}**", "",
            f"- Assistant starts: {a['assistant_starts']} (uncalled: {a['uncalled']})",
            f"- Missed calls: {a['missed_calls']} of {a['calls']}. By language: {lang('missed_call_rate_by_lang')}. "
            f"By seat: {seat('missed_call_rate_by_seat')}",
            f"- Stop commands measurable: {a['stops_applicable']} (not measurable, assistant not talking: "
            f"{a['stops_not_applicable']}). Misses by language: {lang('stop_miss_rate_by_lang')}. "
            f"By seat: {seat('stop_miss_rate_by_seat')}",
            f"- Stop latency p50 {_fmt(a['stop_latency_p50_s'])} s, p95 {_fmt(a['stop_latency_p95_s'])} s",
            f"- *Cuts sentences in half:* assistant started inside a caller's mid-sentence pause "
            f"{a['mid_turn_cutins']} times (of {a['turn_pauses']} pauses)",
            f"- *False stops:* reply cut although nobody said stop: {a['false_stop_cuts']} times "
            f"(people talked during {a['talk_during_reply']} replies)", ""]


def write_report(cfg, results, meta):
    t = cfg["targets"]
    L = ["# QuietGate evaluation report", ""]
    if "holdout" in results:
        h = {k: v["holdout"] for k, v in results["holdout"].items()}
        L += ["## Headline: held-out set (new sentences, built after v2 was frozen)", "",
              f"{meta['holdout']['n']} scenes, {h['baseline']['minutes']} min of synthetic meeting audio "
              f"(seed {cfg['eval']['holdout_seed']}). Nothing was tuned on this set.", ""]
        L += _table(h, t) + [""]
        L += ["### Detail", ""] + _detail(h["quietgate_v1"], "QuietGate v1") + _detail(h["quietgate_v2"], "QuietGate v2")
        L += _detail(h["baseline"], "Naive assistant (before)")
    if "dev" in results:
        d = {k: v["test"] for k, v in results["dev"].items()}
        L += ["## Dev set, test split (scenes 10-29, seed 42)", "",
              "v1's original headline set. Its failures were inspected while designing v2, so v2's numbers here are "
              "**optimistic** and are shown only for continuity.", ""]
        L += _table(d, t) + [""]
    L += ["## Reproducibility", "",
          f"- Config hashes: v2 `{cfg['_hash']}`, v1 `{meta['v1_hash']}`",
          f"- labels.json sha1: " + ", ".join(f"{k} `{v['labels_sha1']}`" for k, v in meta.items() if k in ("dev", "holdout")),
          "- Versions: " + ", ".join(f"{k} {v}" for k, v in meta["versions"].items()),
          "- Models: openWakeWord hey_jarvis_v0.1 (ONNX), Silero VAD (ONNX, bundled with openWakeWord), "
          "vosk-model-small-en-us-0.15, vosk-model-small-ko-0.22; Korean grammar vocabulary config/ko_vocab.txt",
          "- Rerun: `python -m quietgate.cli eval` (uses the shipped audio in data/ and data/holdout/)", ""]
    text = "\n".join(L)
    (RESULTS / "report.md").write_text(text, encoding="utf-8")
    return text


def run(cfg_path=None, workers=4):
    cfg_v2 = load_config(cfg_path)
    cfg_v1 = load_config(V1_CONFIG)
    results, meta = {}, {"v1_hash": cfg_v1["_hash"], "versions": _versions()}
    for set_name in ("dev", "holdout"):
        lab_path = set_dir(set_name) / "labels.json"
        if not lab_path.exists():
            print(f"[{set_name}] no data - skipped (build it with: python -m quietgate.cli make-data --set {set_name})")
            continue
        labels = load_labels(set_name)
        for c in (cfg_v1, cfg_v2):
            detect_all(set_name, c, labels, workers)
        per_sys, timelines = evaluate(set_name, labels, cfg_v2, cfg_v1)
        results[set_name] = per_sys
        meta[set_name] = {"n": len(labels["scenes"]), "labels_sha1": hashlib.sha1(lab_path.read_bytes()).hexdigest()[:12]}
        out = RESULTS / set_name
        out.mkdir(parents=True, exist_ok=True)
        (out / "metrics.json").write_text(json.dumps({"meta": meta[set_name], "targets": cfg_v2["targets"],
                                                      "systems": per_sys}, indent=1), encoding="utf-8")
        (out / "timelines.json").write_text(json.dumps(timelines), encoding="utf-8")
    return write_report(cfg_v2, results, meta)
