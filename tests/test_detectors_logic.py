"""Token logic of the Vosk word detector (no models needed)."""
from quietgate.detectors import _TokenCounter


def test_korean_call_fires_once():
    c = _TokenCounter(["자비스"], reject_next=["씨"])
    assert not c.update("헤이 자비스", final=False)       # waits for the next token
    assert c.update("헤이 자비스 오늘", final=False)
    assert not c.update("헤이 자비스 오늘 안건이", final=False)   # same word, no second fire
    assert not c.update("헤이 자비스 오늘 안건이 뭐야", final=True)


def test_korean_mention_does_not_fire():
    c = _TokenCounter(["자비스"], reject_next=["씨"])
    assert not c.update("자비스", final=False)
    assert not c.update("자비스 씨가 보고서를", final=False)
    assert not c.update("자비스 씨가 보고서를 금요일에", final=True)


def test_stop_prefix_matches_variants():
    c = _TokenCounter(["그만", "멈춰"])
    assert c.update("그만해", final=False)
    c2 = _TokenCounter(["그만", "멈춰"])
    assert c2.update("멈춰 요", final=True)
