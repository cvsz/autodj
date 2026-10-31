import re

from camfrog_autodj.adapters.base import (
    ChatAdapter,
    ChatMessage,
    diff_lines,
    parse_line,
)
from camfrog_autodj.config import Config
from camfrog_autodj.engine import Engine
from camfrog_autodj.library import LocalIndex, host_ok
from camfrog_autodj.models import Track
from camfrog_autodj.playqueue import PlayQueue


def T(n, u="AutoDJ", d=60):
    return Track(f"/m/{n}.mp3", n, d, u)


def test_queue_requests_first_and_peek_stable():
    q = PlayQueue(shuffle=False)
    q.add_pool([T("a"), T("b")])
    assert q.peek().title == "a" and q.peek().title == "a"
    q.add_request(T("req", "bob"))
    assert q.pop().title == "req"
    assert q.pop().title == "a"
    assert q.pop().title == "b"
    assert q.pop().title == "a"  # pool loops


def test_queue_remove_count():
    q = PlayQueue()
    q.add_request(T("x", "Bob"))
    assert q.count_by("bob") == 1 and q.remove(1).title == "x" and q.pop() is None


def test_diff_lines():
    assert diff_lines(["a", "b"], ["a", "b", "c"]) == ["c"]
    assert diff_lines(["a", "b", "c"], ["b", "c", "d"]) == ["d"]
    assert diff_lines(["a"], ["a"]) == []
    assert diff_lines([], ["a"]) == []


def test_parse_line():
    rx = re.compile(Config().line_regex)
    m = parse_line("[12:30] mika_88: !play queen", rx)
    assert (m.user, m.text) == ("mika_88", "!play queen")
    assert parse_line("*** joined the room", rx) is None


def test_host_ok():
    h = ["youtube.com", "youtu.be"]
    assert host_ok("https://www.youtube.com/watch?v=1", h) and host_ok(
        "https://youtu.be/x", h
    )
    assert not host_ok("https://evil.com/youtube.com", h)
    assert not host_ok("https://notyoutube.com/x", h)


class FakeAdapter(ChatAdapter):
    def messages(self):
        return iter(())

    def send(self, text):
        pass


class FakePlayer:
    skipped = False

    def __init__(self):
        self.stopped = 0

    def stop(self):
        self.stopped += 1

    def set_pause(self, v):
        self.paused = v

    def set_volume(self, v):
        self.vol = v


def make():
    e = Engine(
        Config(admins=["Boss"], cooldown=0, voteskip_threshold=2),
        FakeAdapter(),
        player=FakePlayer(),
        index=LocalIndex([]),
    )
    e.resolve = lambda arg, user, admin: [
        Track("https://youtu.be/" + arg.replace(" ", "_"), arg, 120, user)
    ]
    return e


def out(e):
    r = []
    while not e.outbox.empty():
        r.append(e.outbox.get())
    return r


def test_play_np_next_queue():
    e = make()
    e.router.handle(ChatMessage("amy", "!play song one"))
    assert out(e) == ["Queued #1: song one [2:00] for amy"]
    e.current = Track("s", "now", 90, "bob")
    e.router.handle(ChatMessage("amy", "!np"))
    e.router.handle(ChatMessage("amy", "!next"))
    assert out(e) == [
        "Now playing: now [1:30] - requested by bob",
        "Up next: song one [2:00] (amy)",
    ]
    e.router.handle(ChatMessage("amy", "!queue"))
    assert "1) song one" in out(e)[0]


def test_limits_and_permissions():
    e = make()
    for i in range(3):
        e.router.handle(ChatMessage("amy", f"!play s{i}"))
    out(e)
    e.router.handle(ChatMessage("amy", "!play s9"))
    assert "max 3" in out(e)[0]
    e.router.handle(ChatMessage("amy", "!vol 10"))
    assert out(e) == ["amy: admin only"]
    e.router.handle(ChatMessage("boss", "!vol 10"))
    assert out(e) == ["Volume: 10"] and e.player.vol == 10


def test_long_and_live_rejected_for_users():
    e = make()
    e.resolve = lambda a, u, ad: [Track("https://youtu.be/x", "t", 99999, u)]
    e.router.handle(ChatMessage("amy", "!play t"))
    assert "too long" in out(e)[0]
    e.resolve = lambda a, u, ad: [Track("https://youtu.be/x", "t", None, u)]
    e.router.handle(ChatMessage("amy", "!play t"))
    assert "live" in out(e)[0]


def test_skip_and_voteskip():
    e = make()
    e.current = Track("s", "now", 90, "bob")
    e.router.handle(ChatMessage("amy", "!skip"))
    assert "voteskip" in out(e)[0] and e.player.stopped == 0
    e.router.handle(ChatMessage("bob", "!skip"))
    assert e.player.stopped == 1
    out(e)
    e.router.handle(ChatMessage("amy", "!voteskip"))
    e.router.handle(ChatMessage("amy", "!voteskip"))  # same voter counts once
    assert e.player.stopped == 1
    e.router.handle(ChatMessage("cat", "!voteskip"))
    assert e.player.stopped == 2


def test_remove_own_only_and_say_local():
    e = make()
    e.router.handle(ChatMessage("amy", "!play a"))
    out(e)
    e.router.handle(ChatMessage("bob", "!remove 1"))
    assert "only remove your own" in out(e)[0]
    e.router.handle(ChatMessage("amy", "!remove 1"))
    assert out(e) == ["Removed: a"]
    e.router.handle(ChatMessage("console", "!say hello room", local=True))
    assert out(e) == ["hello room"]
    e.router.handle(ChatMessage("amy", "!nonsense"))
    assert out(e) == []
