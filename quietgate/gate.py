"""Turn-taking gates. Pure logic: no audio libraries, so it is unit-testable with plain lists.

TurnGate  (QuietGate, the "after"):  IDLE --wake--> ARMED --caller silent end_of_turn_ms--> SPEAKING
                                     SPEAKING --stop word / reply done--> IDLE
NaiveGate (baseline, the "before"):  replies after any pause of end_of_turn_ms, ignores stop.
"""
from dataclasses import dataclass
from enum import Enum


@dataclass
class Signals:
    t: float          # seconds from stream start (end of the block)
    is_speech: bool   # human speech detected (VAD, with hangover)
    wake: bool        # wake phrase detected in this block
    stop: bool        # stop word detected in this block


class GateEvent(str, Enum):
    START = "start"
    STOP = "stop"


class TurnGate:
    name = "quietgate"

    def __init__(self, end_of_turn_ms=700, armed_timeout_s=8.0, refractory_s=2.0):
        self.eot = end_of_turn_ms / 1000.0
        self.armed_timeout = armed_timeout_s
        self.refractory = refractory_s
        self.state = "IDLE"
        self._armed_at = None
        self._last_speech_t = None
        self._last_wake_t = -1e9

    def step(self, s: Signals, reply_done: bool = False):
        events = []
        if s.is_speech:
            self._last_speech_t = s.t
        wake = s.wake and (s.t - self._last_wake_t) >= self.refractory
        if wake:
            self._last_wake_t = s.t

        if self.state == "SPEAKING":
            if s.stop:
                events.append((s.t, GateEvent.STOP, "SPEAKING"))
                self.state = "IDLE"
            elif reply_done:
                self.state = "IDLE"
        elif self.state == "ARMED":
            if wake:
                # A fresh call while armed (e.g. after a false wake) restarts the wait. Without this,
                # a false wake could swallow the real call that follows it (found in eval, scene_02).
                self._armed_at = s.t
                self._last_speech_t = s.t
            # Stop words are ignored while ARMED: the assistant is silent, and the caller's own request
            # ("...decisions so far") was misheard as "stop" by Vosk, cancelling real calls (found in eval).
            if s.t - self._armed_at > self.armed_timeout:
                self.state = "IDLE"
            elif (not s.is_speech and self._last_speech_t is not None
                  and s.t - self._last_speech_t >= self.eot):
                events.append((s.t, GateEvent.START, "ARMED"))
                self.state = "SPEAKING"
        if self.state == "IDLE" and wake and not events:
            self.state = "ARMED"
            self._armed_at = s.t
            self._last_speech_t = s.t  # the caller is talking right now
        # Hard rule: never start while someone is talking.
        assert not any(e[1] == GateEvent.START for e in events) or not s.is_speech
        return events


class NaiveGate:
    """Typical naive assistant: answers after any pause, cannot be stopped."""
    name = "baseline"

    def __init__(self, end_of_turn_ms=700):
        self.eot = end_of_turn_ms / 1000.0
        self.state = "IDLE"
        self._last_speech_t = None
        self._speech_since_reply = False

    def step(self, s: Signals, reply_done: bool = False):
        events = []
        if s.is_speech:
            self._last_speech_t = s.t
            if self.state == "IDLE":
                self._speech_since_reply = True
        if self.state == "SPEAKING":
            if reply_done:
                self.state = "IDLE"
                self._speech_since_reply = False
        elif (self._speech_since_reply and not s.is_speech
              and s.t - self._last_speech_t >= self.eot):
            events.append((s.t, GateEvent.START, "IDLE"))
            self.state = "SPEAKING"
        return events


def simulate(gate, signals, reply_s):
    """Run a gate over a list of Signals with a simulated reply of reply_s seconds.

    Returns a list of assistant speech intervals [(start, end, ended_by)] and the raw event log.
    ended_by is "stop" (cut by a STOP event), "done" (played fully) or "eos" (stream ended).
    """
    intervals, log = [], []
    cur = None
    for s in signals:
        reply_done = cur is not None and s.t >= cur + reply_s
        if reply_done:
            intervals.append((cur, cur + reply_s, "done"))
            cur = None
        for t, ev, frm in gate.step(s, reply_done=reply_done):
            log.append({"t": round(t, 3), "gate": gate.name, "event": ev.value, "state_from": frm})
            if ev == GateEvent.START:
                cur = t
            elif ev == GateEvent.STOP and cur is not None:
                intervals.append((cur, t, "stop"))
                cur = None
    if cur is not None:
        end = signals[-1].t if signals else cur
        intervals.append((cur, min(cur + reply_s, end), "eos"))
    return intervals, log
