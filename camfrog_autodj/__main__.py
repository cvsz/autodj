import argparse
import logging
import logging.handlers
import os
import shutil
import sys
from pathlib import Path

log = logging.getLogger(__name__)

from . import __version__
from .adapters import NullAdapter, build_adapter
from .config import Config, ConfigError
from .engine import Engine
from .textutil import clean_text


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="camfrog-autodj")
    ap.add_argument("-c", "--config", default="config.toml")
    ap.add_argument("--version", action="version", version=f"AutoDJ {__version__}")
    ap.add_argument(
        "--console", action="store_true", help="chat via stdin/stdout (no Camfrog)"
    )
    ap.add_argument("--gui", action="store_true", help="open the desktop window")
    ap.add_argument("--lang", choices=["en", "th"], help="override config lang")
    ap.add_argument(
        "--check",
        action="store_true",
        help="check the setup (config, mpv, yt-dlp, folders, Camfrog window) and exit",
    )
    ap.add_argument(
        "--discover",
        action="store_true",
        help="find the room window and chat controls, save them to config.toml, then exit",
    )
    ap.add_argument(
        "--windows",
        action="store_true",
        help="list every visible window (exe, pid, class, title) and exit: shows what Camfrog looks like",
    )
    ap.add_argument(
        "--dump",
        metavar="TITLE_RE",
        help="print the control tree of the first window matching TITLE_RE and exit (use > tree.txt)",
    )
    ap.add_argument(
        "--say",
        metavar="TEXT",
        help="send TEXT into the room once and exit (tests chat sending)",
    )
    ap.add_argument(
        "--no-discover", action="store_true", help="skip startup auto-discovery"
    )
    ap.add_argument(
        "--log-file",
        metavar="PATH",
        help="also write the log to PATH (rotating); or set log_file in config",
    )
    ap.add_argument("-v", "--verbose", action="store_true")
    return ap


def _add_log_file(path: str, level: int):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    h = logging.handlers.RotatingFileHandler(
        path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    h.setLevel(level)
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(h)


def main():
    a = _parser().parse_args()
    level = logging.DEBUG if a.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")
    try:
        _run(a, level)
    except ConfigError as ex:
        print(f"\nCannot start: {ex}\n", file=sys.stderr)
        sys.exit(2)
    except RuntimeError as ex:  # e.g. the Camfrog room window is not open
        log.error("%s", ex)
        sys.exit(1)


def _run(a, level):
    if a.windows:
        from .windows import list_all

        for c in list_all():
            print(f"exe={c.exe!r} pid={c.pid} class={c.cls!r} title={c.title!r}")
        return
    if a.dump:
        from pywinauto import Desktop

        from .windows import candidates

        cs = [c for c in candidates(a.dump, visible_only=False) if c.pid != os.getpid()]
        if not cs:
            print("no window matches", a.dump)
            return
        Desktop(backend="uia").window(handle=cs[0].handle).print_control_identifiers()
        return
    if not os.path.exists(a.config) and getattr(
        sys, "frozen", False
    ):  # exe: also look next to AutoDJ.exe
        alt = os.path.join(os.path.dirname(sys.executable), os.path.basename(a.config))
        if os.path.exists(alt):
            a.config = alt
    if os.path.exists(a.config):
        log.info("config: %s", os.path.abspath(a.config))
    else:
        log.warning(
            "config file %s not found: running with built-in defaults (copy config.example.toml to config.toml)",
            os.path.abspath(a.config),
        )
    cfg = Config.load(a.config)
    if a.log_file or cfg.log_file:
        log_path = a.log_file or cfg.log_file
        # Resolve relative log paths to a user-writable directory (APPDATA/Camfrog AutoDJ)
        # instead of CWD which may be Program Files (write-protected).
        if log_path and not os.path.isabs(log_path):
            app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
            log_path = os.path.join(app_data, "Camfrog AutoDJ", log_path)
        try:
            _add_log_file(log_path, level)
        except (OSError, PermissionError):
            log.warning(
                "cannot open log file %s; continuing without file logging",
                log_path,
            )

    # If config file is not writable (e.g. installed to Program Files), relocate to APPDATA
    # so settings changes and auto-discover can be saved.
    p = Path(a.config)
    if not p.exists() or not os.access(p, os.W_OK):
        app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
        app_cfg_dir = Path(app_data) / "Camfrog AutoDJ"
        app_cfg_dir.mkdir(parents=True, exist_ok=True)
        app_cfg_path = app_cfg_dir / "config.toml"
        if p.exists() and not app_cfg_path.exists():
            shutil.copyfile(p, app_cfg_path)
            log.info(
                "config.toml not writable at %s; using %s instead",
                p,
                app_cfg_path,
            )
        p = app_cfg_path
        a.config = str(p)
        cfg = Config.load(str(p))  # re-load from new location
    if a.lang:
        cfg.lang = a.lang
    if a.console:
        cfg.chat_reader = cfg.chat_sender = "console"
    if a.check:
        from . import doctor

        res = doctor.run_checks(cfg)
        print(doctor.format_report(res))
        sys.exit(1 if doctor.has_failures(res) else 0)
    if cfg.auto_launch and "uia" in (cfg.chat_reader, cfg.chat_sender):
        from .launcher import ensure_room

        try:
            ensure_room(cfg)
        except Exception as ex:  # pragma: no cover - defensive; discovery is best-effort
            log.warning(
                "auto-launch failed; continuing without Camfrog: %s", ex
            )
    uses_uia = "uia" in (cfg.chat_reader, cfg.chat_sender)
    if uses_uia and (a.discover or (cfg.auto_discover and not a.no_discover)):
        from . import discover

        # Auto-discovery must never prevent the GUI from opening: log the failure
        # and continue with the existing config instead of crashing at startup.
        try:
            ups = discover.apply(cfg, a.config)
        except Exception:  # pragma: no cover - defensive; discovery is best-effort
            logging.getLogger(__name__).exception("auto-discover failed; continuing without it")
            ups = None
        if a.discover:
            print(ups or "nothing found: open the room window and try again")
            return
    if a.say:
        ad = build_adapter(cfg)
        ad.send(clean_text(a.say))
        print("sent:", a.say)
        return
    try:
        adapter = build_adapter(cfg)
    except Exception as ex:  # Camfrog not open / pywinauto unavailable, ...
        if a.gui:
            # The window must still open so the user can run --check / --discover
            # from inside it; chat degrades to silent until Camfrog is reachable.
            log.error(
                "cannot attach to Camfrog chat (%s); opening the GUI without chat",
                ex,
            )
            adapter = NullAdapter()
        else:
            raise
    eng = Engine(cfg, adapter, cfg_path=a.config)
    if a.gui:
        from .gui import App

        eng.start()
        App(eng).mainloop()
    else:
        eng.run()


if __name__ == "__main__":
    main()
