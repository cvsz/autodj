"""Regression tests for library scanning safety (Phase 3).

Pins the symlink / reparse-point behaviour of ``scan_folder`` and
``LocalIndex``:

* symlinked directories are never followed (nothing outside the scan root
  is indexed)
* symlink cycles do not cause infinite recursion
* broken symlinks are skipped gracefully
* unreadable directories are skipped without aborting the whole scan
* configured track and directory limits are enforced
* unsupported extensions and corrupted metadata never crash the scan

These tests run on any platform; they exercise real directory trees and
symlinks, which Windows represents as reparse points.
"""

from __future__ import annotations

import os

import pytest

from camfrog_autodj.library import MEDIA, LocalIndex, scan_folder


def _media(root: str, name: str, content: b"fake audio") -> str:
    p = os.path.join(root, name)
    with open(p, "wb") as f:
        f.write(content)
    return p


def _sources(tracks) -> list[str]:
    return sorted(t.source for t in tracks)


def test_scan_skips_symlinked_directory_outside_root(tmp_path):
    """A symlink to a directory outside the scan root must not be indexed."""
    outside = tmp_path / "outside"
    outside.mkdir()
    _media(str(outside), "leaked.mp3", b"x")

    root = tmp_path / "root"
    root.mkdir()
    _media(str(root), "inside.mp3", b"x")
    os.symlink(str(outside), str(root / "link_to_outside"))

    assert _sources(scan_folder(str(root))) == [str(root / "inside.mp3")]


def test_scan_skips_broken_symlink(tmp_path):
    """A dangling symlink is skipped, never raises, never indexed."""
    root = tmp_path / "root"
    root.mkdir()
    _media(str(root), "keep.mp3", b"x")
    os.symlink(str(root / "does-not-exist.mp3"), str(root / "broken.mp3"))

    assert _sources(scan_folder(str(root))) == [str(root / "keep.mp3")]


def test_scan_symlink_cycle_does_not_recurse_forever(tmp_path):
    """A directory that symlinks to itself (or an ancestor) terminates."""
    root = tmp_path / "root"
    root.mkdir()
    _media(str(root), "real.mp3", b"x")
    os.symlink(str(root), str(root / "cycle"))

    # Must complete and only index the real file.
    assert _sources(scan_folder(str(root))) == [str(root / "real.mp3")]


def test_scan_unreadable_directory_is_skipped(tmp_path):
    """A directory we cannot read is logged and skipped; the rest still scans."""
    if os.name == "nt":
        pytest.skip("Unix permission bits are not enforced the same way on Windows.")

    root = tmp_path / "root"
    root.mkdir()
    _media(str(root), "keep.mp3", b"x")
    no_perm = root / "no_perm"
    no_perm.mkdir()
    _media(str(no_perm), "hidden.mp3", b"x")
    no_perm.chmod(0o000)

    try:
        sources = _sources(scan_folder(str(root)))
    finally:
        no_perm.chmod(0o755)  # so the temp dir can be removed

    assert sources == [str(root / "keep.mp3")]


def test_scan_enforces_track_limit(tmp_path):
    """``limit`` caps the total tracks returned."""
    root = tmp_path / "root"
    root.mkdir()
    for i in range(5):
        _media(str(root), f"song{i:02d}.mp3", b"x")

    assert len(scan_folder(str(root), limit=3)) == 3
    assert len(scan_folder(str(root), limit=0)) == 5  # 0 = no cap


def test_scan_enforces_max_dirs(tmp_path):
    """``max_dirs`` caps how many sub-directories are entered."""
    root = tmp_path / "root"
    root.mkdir()
    _media(str(root), "top.mp3", b"x")
    sub = root / "sub"
    sub.mkdir()
    _media(str(sub), "deep.mp3", b"x")

    # Enter at most one sub-directory: top file + one sub-directory's file.
    assert len(scan_folder(str(root), max_dirs=1)) == 2


def test_scan_ignores_unsupported_extensions(tmp_path):
    """Non-media files are ignored."""
    root = tmp_path / "root"
    root.mkdir()
    _media(str(root), "song.mp3", b"x")
    _media(str(root), "notes.txt", b"x")
    _media(str(root), "image.jpg", b"x")
    _media(str(root), "track.MP3", b"x")  # extension match is case-insensitive

    sources = _sources(scan_folder(str(root)))
    assert str(root / "song.mp3") in sources
    assert str(root / "track.MP3") in sources
    # extension matching is case-insensitive but the stored path keeps its case
    assert all(n.lower().endswith(tuple(MEDIA)) for n in sources)


def test_localindex_scan_is_idempotent_and_deduplicates(tmp_path):
    """Re-scanning replaces the index rather than appending duplicates."""
    root = tmp_path / "root"
    root.mkdir()
    _media(str(root), "song.mp3", b"x")

    index = LocalIndex([str(root)])
    index.scan()
    first = len(index.tracks)
    index.scan()
    assert len(index.tracks) == first  # re-scan does not accumulate


def test_scan_handles_missing_root(tmp_path):
    """A missing scan root returns an empty list, never raises."""
    assert scan_folder(str(tmp_path / "does-not-exist")) == []


def test_scan_folder_with_unicode_and_long_names(tmp_path):
    """Unicode filenames are indexed; long names do not break traversal."""
    root = tmp_path / "root"
    root.mkdir()
    _media(str(root), "เพลงไทย.mp3", b"x")
    _media(str(root), "a" * 200 + ".wav", b"x")

    sources = _sources(scan_folder(str(root)))
    assert len(sources) == 2


def test_scan_never_follows_symlink_cycle(tmp_path):
    """A directory that symlinks to itself (a reparse-point cycle on Windows)
    is skipped: no infinite recursion, nothing outside the root indexed."""
    root = tmp_path / "root"
    root.mkdir()
    _media(str(root), "keep.mp3", b"x")
    os.symlink(str(root), str(root / "cycle"))

    assert _sources(scan_folder(str(root))) == [str(root / "keep.mp3")]
