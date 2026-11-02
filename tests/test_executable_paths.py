from camfrog_autodj import paths
from camfrog_autodj.library import find_ytdlp


def test_resolve_expands_windows_environment_variables(monkeypatch, tmp_path):
    appdata = tmp_path / "AppData"
    executable = appdata / "Camfrog AutoDJ" / "mpv" / "mpv.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"binary")
    monkeypatch.setenv("APPDATA", str(appdata))

    assert paths.resolve_executable(r"%APPDATA%\Camfrog AutoDJ\mpv\mpv.exe") == str(
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
    monkeypatch.setattr(paths.shutil, "which", lambda name: str(executable) if name == "mpv" else None)

    assert paths.resolve_executable("mpv") == str(executable.resolve())


def test_invalid_explicit_path_does_not_fall_back(monkeypatch):
    monkeypatch.setattr(paths.shutil, "which", lambda _name: "/usr/bin/yt-dlp")

    assert paths.resolve_executable("/missing/yt-dlp", fallback="yt-dlp") == ""


def test_find_ytdlp_expands_appdata_environment_path(monkeypatch, tmp_path):
    appdata = tmp_path / "AppData"
    executable = appdata / "Camfrog AutoDJ" / "mpv" / "yt-dlp.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"binary")
    monkeypatch.setenv("APPDATA", str(appdata))

    assert find_ytdlp(r"%APPDATA%\\Camfrog AutoDJ\\mpv\\yt-dlp.exe") == str(
        executable.resolve()
    )
