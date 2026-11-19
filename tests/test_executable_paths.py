import os

from camfrog_autodj import paths
from camfrog_autodj.library import find_ytdlp


def test_resolve_expands_windows_environment_variables(monkeypatch, tmp_path):
    appdata = tmp_path / "AppData"
    executable = appdata / "CamfrogAutoDJ" / "mpv" / "mpv.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"binary")
    monkeypatch.setenv("APPDATA", str(appdata))

    assert paths.resolve_executable(r"%APPDATA%\CamfrogAutoDJ\mpv\mpv.exe") == str(
        executable.resolve()
    )


def test_resolve_relative_path_from_application_directory(monkeypatch, tmp_path):
    executable = tmp_path / "mpv" / "mpv.exe"
    executable.parent.mkdir()
    executable.write_bytes(b"binary")
    monkeypatch.setattr(paths, "application_dir", lambda: tmp_path)

    assert paths.resolve_executable("mpv/mpv.exe") == str(executable.resolve())


def test_resolve_bare_command_from_path(monkeypatch, tmp_path):
    executable = tmp_path / "mpv"
    executable.write_bytes(b"binary")
    monkeypatch.setattr(
        paths.shutil, "which", lambda name: str(executable) if name == "mpv" else None
    )

    assert paths.resolve_executable("mpv") == str(executable.resolve())


def test_only_exe_never_returns_mpv_com(monkeypatch, tmp_path):
    # A .com shim exists but there is no .exe: fail closed instead of running it.
    com = tmp_path / "mpv.com"
    com.write_bytes(b"shim")
    assert paths.resolve_executable(str(com), only_exe=True) == ""

    # With both present, the sibling .exe is selected.
    exe = tmp_path / "mpv.exe"
    exe.write_bytes(b"binary")
    assert paths.resolve_executable(str(com), only_exe=True) == str(exe.resolve())


def test_only_exe_asks_path_for_exe(monkeypatch, tmp_path):
    exe = tmp_path / "mpv.exe"
    exe.write_bytes(b"binary")
    calls = []

    def fake_which(name):
        calls.append(name)
        return str(exe) if name == "mpv.exe" else str(tmp_path / "mpv.com")

    monkeypatch.setattr(paths.shutil, "which", fake_which)
    assert paths.resolve_executable("mpv", only_exe=True) == str(exe.resolve())
    assert calls == ["mpv.exe" if os.name == "nt" else "mpv"]


def test_player_never_launches_mpv_com(monkeypatch):
    from camfrog_autodj.config import Config
    from camfrog_autodj.player import MpvPlayer

    monkeypatch.setattr("camfrog_autodj.player.resolve_executable", lambda *_a, **_k: "")
    configured = "D:/tools/mpv.com" if os.name == "nt" else "/tools/mpv.com"
    player = MpvPlayer(Config(mpv_path=configured))
    if os.name == "nt":
        assert player._mpv_executable().lower().endswith("mpv.exe")
        assert all(not arg.lower().endswith(".com") for arg in player._base())


def test_log_path_defaults_to_install_logs_folder(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "application_dir", lambda: tmp_path)
    assert paths.resolve_log_path(None) == tmp_path / "logs" / "autodj.log"
    assert paths.resolve_log_path("autodj.log") == tmp_path / "logs" / "autodj.log"
    assert (tmp_path / "logs").is_dir()
    custom = tmp_path / "logs" / "custom.log"
    assert paths.resolve_log_path(str(custom)) == custom


def test_invalid_explicit_path_does_not_fall_back(monkeypatch):
    monkeypatch.setattr(paths.shutil, "which", lambda _name: "/usr/bin/yt-dlp")

    assert paths.resolve_executable("/missing/yt-dlp", fallback="yt-dlp") == ""


def test_find_ytdlp_expands_appdata_environment_path(monkeypatch, tmp_path):
    appdata = tmp_path / "AppData"
    # The expansion uses "Camfrog AutoDJ" (with space); create the file matching that path
    executable = appdata / "Camfrog AutoDJ" / "mpv" / "yt-dlp.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"binary")
    monkeypatch.setenv("APPDATA", str(appdata))

    assert find_ytdlp(r"%APPDATA%\Camfrog AutoDJ\mpv\yt-dlp.exe") == str(executable.resolve())
