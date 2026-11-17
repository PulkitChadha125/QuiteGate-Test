"""Acceptance-test metrics. Pure functions over ground-truth labels and assistant speech intervals."""
import numpy as np


def scene_metrics(label, intervals, cfg_eval):
    """label: scene label dict (ground truth). intervals: [(start, end, ended_by)] of assistant speech."""
    calls, stops, speech = label["calls"], label["stops"], label["speech"]
    starts = [a[0] for a in intervals]
    w_unc = cfg_eval["uncalled_window_s"]
    w_miss = cfg_eval["missed_call_window_s"]

    # An assistant start is "uncalled" if no wake call ended within the previous w_unc seconds.
    uncalled = sum(1 for t in starts
                   if not any(c["start"] <= t and t - c["end"] <= w_unc for c in calls))
    # A "talk-over start" is an assistant start while a human is speaking (ground truth).
    talk_over = sum(1 for t in starts if any(s[0] < t < s[1] for s in speech))

    call_rows = []
    for c in calls:
        hit = [t for t in starts if c["start"] <= t <= c["end"] + w_miss]
        call_rows.append({"lang": c["lang"], "hit": bool(hit),
                          "delay": (min(hit) - c["end"]) if hit else None})

    stop_rows = []
    for st in stops:
        # A stop command is only measurable if the assistant was talking when it was said.
        a = next((a for a in intervals if a[0] <= st["start"] < a[1]), None)
        if a is None:
            stop_rows.append({"lang": st["lang"], "applicable": False})
            continue
        lat = max(0.0, a[1] - st["end"])
        stop_rows.append({"lang": st["lang"], "applicable": True, "latency": lat,
                          "miss": lat > cfg_eval["stop_miss_s"]})
    return {"duration": label["duration"], "starts": len(starts), "uncalled": uncalled,
            "talk_over": talk_over, "calls": call_rows, "stops": stop_rows}


def _by_lang(items, fn):
    out = {}
    for lang in ("en", "ko"):
        sub = [i for i in items if i["lang"] == lang]
        out[lang] = {"n": len(sub), "value": fn(sub) if sub else None}
    return out


def aggregate(rows):
    dur = sum(r["duration"] for r in rows)
    calls = [c for r in rows for c in r["calls"]]
    stops = [s for r in rows for s in r["stops"] if s["applicable"]]
    delays = [c["delay"] for c in calls if c["hit"]]
    lats = [s["latency"] for s in stops]
    n_unc = sum(r["uncalled"] for r in rows)
    n_miss = sum(1 for c in calls if not c["hit"])
    return {
        "minutes": round(dur / 60, 2),
        "assistant_starts": sum(r["starts"] for r in rows),
        "uncalled": n_unc,
        "uncalled_per_10min": round(n_unc / dur * 600, 2) if dur else None,
        "talk_over_starts": sum(r["talk_over"] for r in rows),
        "calls": len(calls),
        "missed_calls": n_miss,
        "missed_call_rate": round(n_miss / len(calls), 3) if calls else None,
        "missed_call_rate_by_lang": _by_lang(calls, lambda s: round(sum(not c["hit"] for c in s) / len(s), 3)),
        "reply_delay_median_s": round(float(np.median(delays)), 3) if delays else None,
        "stops_applicable": len(stops),
        "stops_not_applicable": sum(1 for r in rows for s in r["stops"] if not s["applicable"]),
        "stop_latency_p50_s": round(float(np.percentile(lats, 50)), 3) if lats else None,
        "stop_latency_p95_s": round(float(np.percentile(lats, 95)), 3) if lats else None,
        "stop_miss_rate": round(sum(s["miss"] for s in stops) / len(stops), 3) if stops else None,
        "stop_miss_rate_by_lang": _by_lang(stops, lambda s: round(sum(x["miss"] for x in s) / len(s), 3)),
    }


METRIC_KEYS = ["uncalled_per_10min", "talk_over_starts", "missed_call_rate",
               "stop_latency_p95_s", "stop_miss_rate", "reply_delay_median_s"]


def check_targets(agg, targets):
    """Return {metric: (value, target, passed)}. All targets are 'lower or equal is better'."""
    out = {}
    for k in METRIC_KEYS:
        v, t = agg.get(k), targets[k]
        out[k] = (v, t, v is not None and v <= t)
    return out
