"""Test that TTS volume ducking works correctly with real player behavior."""

from unittest.mock import MagicMock, patch

from camfrog_autodj.adapters import NullAdapter
from camfrog_autodj.config import Config
from camfrog_autodj.engine import Engine
from camfrog_autodj.player import MpvPlayer


def test_tts_ducks_music_volume_real_player():
    """TTS should duck music volume during playback and restore after.

    This test simulates the real player behavior where _ipc is None
    before play_file is called, so set_volume returns False.
    """
    cfg = Config()
    cfg.tts_duck = 25
    cfg.volume = 70
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    # Create a mock player that simulates real behavior:
    # - set_volume returns False when _ipc is None
    # - play_file sets _ipc and then blocks
    mock_player = MagicMock(spec=MpvPlayer)
    mock_player._ipc = None
    mock_player._lock = MagicMock()
    mock_player._lock.__enter__ = MagicMock(return_value=mock_player._lock)
    mock_player._lock.__exit__ = MagicMock(return_value=False)

    def set_volume_side_effect(v):
        if mock_player._ipc is None:
            return False
        return True

    mock_player.set_volume.side_effect = set_volume_side_effect

    def play_file_side_effect(path, duck_volume=None):
        # Simulate play_file setting up IPC
        mock_player._ipc = "/fake/ipc/path"
        # Apply duck volume if provided
        if duck_volume is not None:
            mock_player.set_volume(duck_volume)
        # Simulate playback
        import time

        time.sleep(0.01)
        mock_player._ipc = None

    mock_player.play_file.side_effect = play_file_side_effect

    eng.player = mock_player
    eng.volume = 70

    with patch("camfrog_autodj.tts.synth"):
        with patch("tempfile.gettempdir", return_value="/tmp"):
            eng.speak("test")

    # Wait for the job to complete
    eng.exec.shutdown(wait=True)

    # Verify volume calls
    calls = mock_player.set_volume.call_args_list
    print(f"Volume calls: {calls}")

    # With the fix, duck volume (25) should be called during play_file
    # and restore volume (70) should be called in finally block
    assert len(calls) >= 2, f"Expected at least 2 volume calls, got {len(calls)}"
    # The duck call should be 25
    assert calls[0][0][0] == 25, f"Expected first call to be duck volume (25), got {calls[0][0][0]}"
    # The restore call should be 70
    assert calls[-1][0][0] == 70, (
        f"Expected last call to be restored volume (70), got {calls[-1][0][0]}"
    )
