"""Test that doctor.py skips symlinks."""

import tempfile
from pathlib import Path

from camfrog_autodj.doctor import _count_media_files


def test_doctor_skips_symlinks():
    """_count_media_files should skip symlinks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        music_dir = Path(tmpdir) / "music"
        music_dir.mkdir()

        # Create a real media file
        real_file = music_dir / "real.mp3"
        real_file.write_bytes(b"fake mp3")

        # Create a directory outside music_dir
        outside_dir = Path(tmpdir) / "outside"
        outside_dir.mkdir()
        outside_file = outside_dir / "secret.mp3"
        outside_file.write_bytes(b"secret")

        # Create symlink in music_dir pointing to outside file
        symlink = music_dir / "link.mp3"
        symlink.symlink_to(outside_file)

        # Count should only include real.mp3, not the symlink
        count = _count_media_files(music_dir)
        assert count == 1, f"Expected 1 file, got {count}"


def test_doctor_skips_symlink_directories():
    """_count_media_files should not follow symlink directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        music_dir = Path(tmpdir) / "music"
        music_dir.mkdir()

        # Create a real media file
        real_file = music_dir / "real.mp3"
        real_file.write_bytes(b"fake mp3")

        # Create a directory outside music_dir with media files
        outside_dir = Path(tmpdir) / "outside"
        outside_dir.mkdir()
        (outside_dir / "secret1.mp3").write_bytes(b"secret1")
        (outside_dir / "secret2.mp3").write_bytes(b"secret2")

        # Create symlink directory in music_dir pointing to outside dir
        symlink_dir = music_dir / "outside_link"
        symlink_dir.symlink_to(outside_dir)

        # Count should only include real.mp3, not files in symlink directory
        count = _count_media_files(music_dir)
        assert count == 1, f"Expected 1 file, got {count}"
