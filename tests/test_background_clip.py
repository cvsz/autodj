from camfrog_autodj.clipkeys import clip_action
from camfrog_autodj.winmsg import make_lparam, pick_child, utf16_units


def test_utf16_units_thai_and_emoji():
    assert utf16_units("ก!") == [0x0E01, 0x21]
    assert utf16_units("\U0001F600") == [0xD83D, 0xDE00]  # surrogate pair


def test_lparam_and_negative_coords():
    assert make_lparam(10, 20) == (20 << 16) | 10
    assert make_lparam(-1, 5) & 0xFFFF == 0xFFFF  # negative x wraps to 16 bits


def test_pick_child_smallest_containing():
    rects = [(1, (0, 0, 1000, 800)), (2, (500, 600, 1100, 700)), (3, (513, 688, 1122, 723))]
    assert pick_child(rects, (800, 700)) == 3  # message box wins over the big parents
    assert pick_child(rects, (100, 100)) == 1
    assert pick_child(rects, (5000, 5000)) is None


def test_clip_thai_layout_only():
    # Thai layout: keysym is a Thai letter, so Tk's own Ctrl+V binding does not fire: we handle it
    assert clip_action(86, "Thai_phophan") == "paste"
    assert clip_action(67, "Thai_ae") == "copy"
    assert clip_action(65, "Thai_phophung") == "all"
    # Latin layout: Tk already handles it: no double paste
    assert clip_action(86, "v") is None and clip_action(67, "C") is None
    assert clip_action(45, "Insert") == "copy" and clip_action(45, "Insert", shift=True) == "paste"
    assert clip_action(86, "Thai_phophan", windows=False) is None
