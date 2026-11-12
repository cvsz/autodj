"""Test that admin path traversal is prevented."""

import os
import tempfile

from camfrog_autodj.adapters import NullAdapter
from camfrog_autodj.config import Config
from camfrog_autodj.engine import Engine
from camfrog_autodj.exceptions import UserError


def test_admin_cannot_escape_music_dirs():
    """Admin should not be able to access files outside music_dirs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        music_dir = os.path.join(tmpdir, "music")
        os.makedirs(music_dir)

        cfg = Config()
        cfg.music_dirs = [music_dir]
        cfg.admins = ["admin"]
        adapter = NullAdapter()
        eng = Engine(cfg, adapter)

        # Try to access file outside music_dir
        outside_file = os.path.join(tmpdir, "secret.txt")
        with open(outside_file, "w") as f:
            f.write("secret")

        try:
            eng._resolve_local_file(outside_file, "admin", admin=True)
            raise AssertionError("Should have raised UserError")
        except UserError as e:
            print(f"Got expected error: {e}")
            assert "folders are admin only" in str(e) or "not in lib" in str(e)


def test_admin_cannot_escape_with_empty_music_dirs():
    """Admin should not be able to access files when music_dirs is empty.

    This is a security vulnerability: when music_dirs is empty, the admin
    check is skipped and admins can access any file on the filesystem.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = Config()
        cfg.music_dirs = []  # Empty music dirs
        cfg.admins = ["admin"]
        adapter = NullAdapter()
        eng = Engine(cfg, adapter)

        # Try to access any file
        outside_file = os.path.join(tmpdir, "secret.txt")
        with open(outside_file, "w") as f:
            f.write("secret")

        try:
            eng._resolve_local_file(outside_file, "admin", admin=True)
            # With empty music_dirs, the current code allows it (BUG)
            print("VULNERABILITY: Admin can access files when music_dirs is empty!")
            raise AssertionError(
                "Should have raised UserError - admin path traversal vulnerability"
            )
        except UserError as e:
            print(f"Got expected error: {e}")
            assert (
                "folders are admin only" in str(e)
                or "not in lib" in str(e)
                or "music_dirs" in str(e).lower()
            )


def test_non_admin_cannot_access_outside_library():
    """Non-admin should not be able to access files outside library."""
    with tempfile.TemporaryDirectory() as tmpdir:
        music_dir = os.path.join(tmpdir, "music")
        os.makedirs(music_dir)

        cfg = Config()
        cfg.music_dirs = [music_dir]
        cfg.admins = ["admin"]
        adapter = NullAdapter()
        eng = Engine(cfg, adapter)

        # Try to access file outside music_dir as non-admin
        outside_file = os.path.join(tmpdir, "secret.txt")
        with open(outside_file, "w") as f:
            f.write("secret")

        try:
            eng._resolve_local_file(outside_file, "user", admin=False)
            raise AssertionError("Should have raised UserError")
        except UserError as e:
            print(f"Got expected error: {e}")
            assert "file is not in the music library" in str(e) or "folders are admin only" in str(
                e
            )
