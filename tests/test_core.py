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
    peeked = q.peek()
    assert peeked is not None and peeked.title == "a"
    peeked2 = q.peek()
    assert peeked2 is not None and peeked2.title == "a"
    q.add_request(T("req", "bob"))
    popped = q.pop()
    assert popped is not None and popped.title == "req"
    popped2 = q.pop()
    assert popped2 is not None and popped2.title == "a"
    popped3 = q.pop()
    assert popped3 is not None and popped3.title == "b"
    popped4 = q.pop()
    assert popped4 is not None and popped4.title == "a"  # pool loops


def test_queue_remove_count():
    q = PlayQueue()
    q.add_request(T("x", "Bob"))
    assert q.count_by("bob") == 1
    removed = q.remove(1)
    assert removed is not None and removed.title == "x"
    assert q.pop() is None


def test_diff_lines():
    assert diff_lines(["a", "b"], ["a", "b", "c"]) == ["c"]
    assert diff_lines(["a", "b", "c"], ["b", "c", "d"]) == ["d"]
    assert diff_lines(["a"], ["a"]) == []
    assert diff_lines([], ["a"]) == []


def test_parse_line():
    rx = re.compile(Config().line_regex)
    m = parse_line("[12:30] mika_88: !play queen", rx)
    assert m is not None
    assert (m.user, m.text) == ("mika_88", "!play queen")
    assert parse_line("*** joined the room", rx) is None


def test_host_ok():
    h = ["youtube.com", "youtu.be"]
    assert host_ok("https://www.youtube.com/watch?v=1", h) and host_ok("https://youtu.be/x", h)
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

    def get_time_pos(self):
        # Simulate IPC unavailable -> engine falls back to wall-clock
        return None


def make():
    e = Engine(
        Config(
            admins=["Boss"],
            cooldown=0,
            voteskip_threshold=2,
            admin_block_user=True,
            admin_unblock_user=True,
            admin_block_bot=True,
            admin_unblock_bot=True,
            admin_kick_user=True,
            admin_ban_user=True,
            admin_unban_user=True,
            admin_punish_user=True,
            admin_punish_bot=True,
            admin_delete_message_enabled=True,
        ),
        FakeAdapter(),
        player=FakePlayer(),
        index=LocalIndex([]),
    )
    e.resolve = lambda arg, user, admin: [  # type: ignore[method-assign]
        Track("https://youtu.be/" + arg.replace(" ", "_"), arg, 120, user)
    ]
    return e


def make_im():
    """Create engine for IM command testing (play commands work in IM)."""
    e = make()
    return e


def out(e):
    r = []
    while not e.outbox.empty():
        r.append(e.outbox.get())
    return r


def test_play_np_next_queue():
    e = make()
    e._active_room_users.add("amy")
    e.router.handle(ChatMessage("amy", "play song one", is_im=True))
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
    e._active_room_users.add("amy")
    for i in range(3):
        e.router.handle(ChatMessage("amy", f"play s{i}", is_im=True))
    out(e)
    e.router.handle(ChatMessage("amy", "play s9", is_im=True))
    assert "max 3" in out(e)[0]
    e.router.handle(ChatMessage("amy", "!vol 10"))
    assert out(e) == ["amy: admin only"]
    e.router.handle(ChatMessage("boss", "!vol 10"))
    assert out(e) == ["Volume: 10"] and e.player.vol == 10


def test_long_and_live_rejected_for_users():
    e = make()
    e._active_room_users.add("amy")
    e.resolve = lambda a, u, ad: [Track("https://youtu.be/x", "t", 99999, u)]
    e.router.handle(ChatMessage("amy", "play t", is_im=True))
    assert "too long" in out(e)[0]
    e.resolve = lambda a, u, ad: [Track("https://youtu.be/x", "t", None, u)]
    e.router.handle(ChatMessage("amy", "play t", is_im=True))
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
    e._active_room_users.add("amy")
    e.router.handle(ChatMessage("amy", "play a", is_im=True))
    out(e)
    e.router.handle(ChatMessage("bob", "!remove 1"))
    assert "only remove your own" in out(e)[0]
    e.router.handle(ChatMessage("amy", "!remove 1"))
    assert out(e) == ["Removed: a"]
    e.router.handle(ChatMessage("console", "!say hello room", local=True))
    assert out(e) == ["hello room"]
    e.router.handle(ChatMessage("amy", "!nonsense"))
    assert out(e) == []


def test_local_index_find_preserves_substring_semantics_with_precomputed_hay():
    """find() must keep exact substring matching ("love" matches "Lovely") while
    avoiding rebuilding the lowercase search string on every call."""
    from pathlib import Path

    from camfrog_autodj.library import LocalIndex

    index = LocalIndex(["/music"])
    index.tracks = [
        Track("/music/Amazing Grace.mp3", "Amazing Grace", 120, "u"),
        Track("/music/Lovely Day.mp3", "Lovely Day", 200, "u"),
        Track("/music/Love Song.mp3", "Love Song", 180, "u"),
    ]
    index._hay = [f"{t.title} {Path(t.source).name}".lower() for t in index.tracks]

    hit = index.find("love", "amy")
    assert hit is not None and hit.title == "Lovely Day"  # substring, first in order

    hit = index.find("amazing grace", "amy")
    assert hit is not None and hit.title == "Amazing Grace"  # multi-word, all must match

    assert index.find("nonexistent", "amy") is None
    assert index.find("", "amy") is None


def test_playqueue_version_bumps_on_every_mutation():
    """The queue exposes a monotonic version so GUI polls can skip rebuilds when unchanged."""
    from camfrog_autodj.playqueue import PlayQueue

    q = PlayQueue(shuffle=False)
    v0 = q.version
    assert not q.changed_since(v0)  # fresh queue: no change since its own version

    q.add_request(Track("s1", "one", 60, "amy"))
    v1 = q.version
    assert q.changed_since(v0) and v1 > v0

    q.add_pool([Track("p1", "pool", 60, "sys"), Track("p1", "pool", 60, "sys")])
    v2 = q.version
    assert v2 > v1 and not q.changed_since(v2)

    q.set_shuffle(True)
    assert q.changed_since(v2)

    q.remove(1)
    v3 = q.version
    assert q.changed_since(v2) and not q.changed_since(v3)

    q.remove_track(Track("nonexistent", "x", 0, "u"))  # no-op must NOT bump
    assert q.version == v3 and not q.changed_since(v3)

    q.clear()
    assert q.changed_since(v3)


def test_engine_chat_and_im_snapshot_versions():
    """Engine chat_snapshot and im_snapshot return version counters for efficient GUI polling."""
    from camfrog_autodj.adapters import NullAdapter
    from camfrog_autodj.config import Config
    from camfrog_autodj.engine import Engine

    class FakePlayer:
        skipped = False

        def stop(self):
            pass

        def set_pause(self, v):
            return True

        def set_volume(self, v):
            pass

        def get_time_pos(self):
            return None

        def available(self):
            return True

    cfg = Config(admins=["Boss"], cooldown=0)
    adapter = NullAdapter()
    eng = Engine(cfg, adapter, player=FakePlayer())

    # Initial snapshots
    seq1, ver1, logs1 = eng.chat_snapshot()
    im_seq1, im_ver1, im_logs1 = eng.im_snapshot()
    assert seq1 == 0
    assert ver1 == 0
    assert im_seq1 == 0
    assert im_ver1 == 0

    # Log a chat message
    eng.log_chat("user1", "hello")
    seq2, ver2, logs2 = eng.chat_snapshot()
    assert seq2 == 1
    assert ver2 == 1
    assert len(logs2) == 1

    # Log another chat message
    eng.log_chat("user2", "world")
    seq3, ver3, logs3 = eng.chat_snapshot()
    assert seq3 == 2
    assert ver3 == 2

    # IM log
    from camfrog_autodj.adapters.base import ChatMessage

    eng._log_im_message(ChatMessage("user1", "private msg", is_im=True))
    im_seq2, im_ver2, im_logs2 = eng.im_snapshot()
    assert im_seq2 == 1
    assert im_ver2 == 1
    assert len(im_logs2) == 1

    # Version should only change when log actually changes
    # Calling snapshot without changes should return same version
    seq4, ver4, _ = eng.chat_snapshot()
    assert seq4 == 2
    assert ver4 == 2  # version unchanged

    im_seq3, im_ver3, _ = eng.im_snapshot()
    assert im_seq3 == 1
    assert im_ver3 == 1  # version unchanged
