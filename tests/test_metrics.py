from quietgate.metrics import scene_metrics, aggregate

CFG = {"uncalled_window_s": 8.0, "missed_call_window_s": 3.0, "stop_miss_s": 1.5}
LABEL = {
    "duration": 60.0,
    "speech": [[0, 5, "a", "en"], [10, 12, "b", "en"], [20, 21, "c", "en"]],
    "calls": [{"start": 10, "end": 12, "lang": "en"}],
    "stops": [{"start": 20, "end": 21, "lang": "en"}],
}


def test_good_gate():
    a = aggregate([scene_metrics(LABEL, [(12.8, 21.3, "stop")], CFG)])
    assert a["uncalled"] == 0 and a["talk_over_starts"] == 0 and a["missed_calls"] == 0
    assert abs(a["reply_delay_median_s"] - 0.8) < 1e-9
    assert abs(a["stop_latency_p95_s"] - 0.3) < 1e-9
    assert a["stop_miss_rate"] == 0


def test_bad_gate():
    a = aggregate([scene_metrics(LABEL, [(4.0, 9.0, "done"), (12.8, 26.0, "done"), (40, 46, "done")], CFG)])
    assert a["uncalled"] == 2            # starts at 4.0 and 40 have no call in the preceding 8 s
    assert a["talk_over_starts"] == 1    # 4.0 is inside human speech 0..5
    assert a["uncalled_per_10min"] == 20.0
    assert a["stop_miss_rate"] == 1.0    # kept talking 26 - 21 = 5 s > 1.5 s


def test_missed_call_and_na_stop():
    a = aggregate([scene_metrics(LABEL, [], CFG)])
    assert a["missed_call_rate"] == 1.0
    assert a["stops_applicable"] == 0 and a["stops_not_applicable"] == 1
