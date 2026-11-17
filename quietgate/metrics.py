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

    gain = {s["id"]: s.get("gain_db", 0.0) for s in label.get("speakers", [])}

    def seat(spk_id):
        # near = 0 to -6 dB, far = -6 to -12 dB (speaker gain imitates distance from the device)
        return "far" if gain.get(spk_id, 0.0) < -6 else "near"

    call_rows = []
    for c in calls:
        hit = [t for t in starts if c["start"] <= t <= c["end"] + w_miss]
        call_rows.append({"lang": c["lang"], "seat": seat(c.get("speaker")), "hit": bool(hit),
                          "delay": (min(hit) - c["end"]) if hit else None})

    stop_rows = []
    for st in stops:
        # A stop command is only measurable if the assistant was talking when it was said.
        a = next((a for a in intervals if a[0] <= st["start"] < a[1]), None)
        if a is None:
            stop_rows.append({"lang": st["lang"], "seat": seat(st.get("speaker")), "applicable": False})
            continue
        lat = max(0.0, a[1] - st["end"])
        stop_rows.append({"lang": st["lang"], "seat": seat(st.get("speaker")), "applicable": True,
                          "latency": lat, "miss": lat > cfg_eval["stop_miss_s"]})

    # Diagnostics for the brief's other complaints (not part of the pre-registered pass/fail test):
    # "cuts sentences in half": assistant starts inside a mid-sentence pause of the caller.
    mid_turn = sum(1 for t in starts for p in label.get("turn_pauses", []) if p[0] < t < p[1])
    # false stop: reply cut by a "stop" event although nobody said a stop word.
    false_cuts = sum(1 for a in intervals if a[2] == "stop"
                     and not any(st["start"] - 0.2 <= a[1] <= st["end"] + cfg_eval["stop_miss_s"] for st in stops))
    return {"duration": label["duration"], "starts": len(starts), "uncalled": uncalled,
            "talk_over": talk_over, "calls": call_rows, "stops": stop_rows,
            "mid_turn_cutins": mid_turn, "turn_pauses": len(label.get("turn_pauses", [])),
            "false_stop_cuts": false_cuts, "talk_during_reply": len(label.get("talk_during_reply", []))}


def _by(items, key, values, fn):
    out = {}
    for v in values:
        sub = [i for i in items if i.get(key) == v]
        out[v] = {"n": len(sub), "value": fn(sub) if sub else None}
    return out


def _by_lang(items, fn):
    return _by(items, "lang", ("en", "ko"), fn)


def _by_seat(items, fn):
    return _by(items, "seat", ("near", "far"), fn)


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
        "missed_call_rate_by_seat": _by_seat(calls, lambda s: round(sum(not c["hit"] for c in s) / len(s), 3)),
        "stop_miss_rate_by_seat": _by_seat(stops, lambda s: round(sum(x["miss"] for x in s) / len(s), 3)),
        "mid_turn_cutins": sum(r.get("mid_turn_cutins", 0) for r in rows),
        "turn_pauses": sum(r.get("turn_pauses", 0) for r in rows),
        "false_stop_cuts": sum(r.get("false_stop_cuts", 0) for r in rows),
        "talk_during_reply": sum(r.get("talk_during_reply", 0) for r in rows),
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
