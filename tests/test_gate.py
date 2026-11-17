from quietgate.gate import Signals, TurnGate, NaiveGate, GateEvent, simulate

DT = 0.08


def seq(spec):
    """spec: list of (n_blocks, is_speech, wake, stop) -> list[Signals]. wake/stop fire on the first block only."""
    out, t = [], 0.0
    for n, sp, wk, st in spec:
        for i in range(n):
            t += DT
            out.append(Signals(round(t, 3), sp, wk and i == 0, st and i == 0))
    return out


def test_quiet_without_wake():
    sig = seq([(20, True, False, False), (20, False, False, False),
               (20, True, False, False), (30, False, False, False)])
    iv, _ = simulate(TurnGate(), sig, reply_s=3)
    assert iv == []


def test_naive_talks_after_every_pause():
    sig = seq([(20, True, False, False), (20, False, False, False),
               (20, True, False, False), (20, False, False, False)])
    iv, _ = simulate(NaiveGate(), sig, reply_s=1.0)
    assert len(iv) == 2


def test_wake_then_waits_for_end_of_turn():
    sig = seq([(5, True, True, False), (15, True, False, False), (20, False, False, False)])
    iv, _ = simulate(TurnGate(end_of_turn_ms=700), sig, reply_s=5)
    assert len(iv) == 1
    start, last_speech = iv[0][0], 20 * DT
    assert 0.7 - 1e-9 <= start - last_speech < 0.7 + DT + 1e-9


def test_never_starts_while_speech():
    # Wake, then someone keeps talking for the whole armed window: must never start, then time out.
    sig = seq([(1, True, True, False), (120, True, False, False), (10, False, False, False)])
    g = TurnGate(armed_timeout_s=8.0)
    for s in sig:
        for _, ev, _ in g.step(s):
            assert not (ev == GateEvent.START and s.is_speech)
    iv, _ = simulate(TurnGate(armed_timeout_s=8.0), sig, reply_s=3)
    assert iv == []


def test_stop_cuts_reply_immediately():
    sig = seq([(5, True, True, False), (10, False, False, False),
               (3, True, False, True), (40, False, False, False)])
    iv, _ = simulate(TurnGate(end_of_turn_ms=700), sig, reply_s=10)
    assert len(iv) == 1 and iv[0][2] == "stop"
    assert abs(iv[0][1] - (5 + 10 + 1) * DT) < 1e-6


def test_naive_ignores_stop():
    sig = seq([(10, True, False, False), (10, False, False, False),
               (2, True, False, True), (100, False, False, False)])
    iv, _ = simulate(NaiveGate(), sig, reply_s=4)
    assert iv[0][2] == "done"


def test_new_wake_rearms_after_false_wake():
    # false wake, 6 s of chatter, real wake, 3 s more speech, then silence -> must answer the real call
    sig = seq([(1, True, True, False), (75, True, False, False), (1, True, True, False),
               (37, True, False, False), (30, False, False, False)])
    iv, _ = simulate(TurnGate(armed_timeout_s=8.0), sig, reply_s=1)
    assert len(iv) == 1


def test_refractory_blocks_double_wake():
    g = TurnGate(refractory_s=2.0)
    g.step(Signals(0.08, True, True, False))
    assert g.state == "ARMED"
    g.state = "IDLE"
    g.step(Signals(0.5, True, True, False))
    assert g.state == "IDLE"
