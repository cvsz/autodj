"""diff_lines: new lines only, whatever the read window did."""

from autodj.adapters.base import diff_lines


def test_growth():
    assert diff_lines(["a", "b"], ["a", "b", "c"]) == ["c"]


def test_trimmed_top():
    assert diff_lines(["a", "b", "c"], ["b", "c", "d"]) == ["d"]


def test_no_change():
    assert diff_lines(["a", "b"], ["a", "b"]) == []


def test_baseline_and_empty():
    assert diff_lines([], ["a"]) == []
    assert diff_lines(["a"], []) == []


def test_window_shifted_earlier_does_not_replay_old_lines():
    """Live bug: the fixed-size tail started one item earlier after a separator vanished."""
    req = "6:35|!play song"
    prev = ["5:10|!ask", "5:23|!ask", "6:07|!ask", req]
    cur = ["5:05|older", "5:10|!ask", "5:23|!ask", "6:07|!ask", req]  # one older item in front
    assert diff_lines(prev, cur) == []
    assert diff_lines(prev, cur + ["6:35|reply"]) == ["6:35|reply"]


def test_same_message_sent_twice_is_new():
    prev = ["6:30|hi", "6:35|!play x"]
    assert diff_lines(prev, prev + ["6:35|!play x"]) == ["6:35|!play x"]


def test_full_replacement_returns_all():
    assert diff_lines(["a", "b"], ["x", "y"]) == ["x", "y"]
