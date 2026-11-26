"""FFmpeg transcoder worker pool.

Ported from cvsz/streamdbc internal/transcoder/worker.go.

Transcodes an input file to HLS at multiple ABR resolutions using FFmpeg.
Each stream can have at most one active transcoding job.  Hardware encoder
detection (NVENC, QSV, AMF, VideoToolbox) is supported with a libx264
software fallback.

AutoDJ uses this to produce adaptive-bitrate HLS playlists from recorded
broadcasts for playback on any platform.
"""

from __future__ import annotations

import contextlib
import logging
import os
import queue
import shutil
import subprocess  # nosec B404
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .stream_id import validate_stream_id

_LOG = logging.getLogger("autodj.stream")


class TranscoderError(Exception):
    """Transcoder manager error."""


class ManagerNotStartedError(TranscoderError):
    """The transcoder manager has not been started."""


class ManagerStoppedError(TranscoderError):
    """The transcoder manager has been stopped."""


class InvalidJobError(TranscoderError):
    """An invalid transcode job was submitted."""


class DuplicateJobError(TranscoderError):
    """A transcode job with the same ID already exists."""


class StreamBusyError(TranscoderError):
    """A stream already has an active transcoding job."""


_MAX_TRANSCODER_WORKERS = 16
_MAX_TRANSCODER_DIMENSION = 4096
_MAX_TRANSCODER_BITRATE = 50_000_000
_MAX_TRANSCODER_FRAME_RATE = 120
_MAX_TRANSCODER_AUDIO_BITRATE = 512_000

_MAX_FFMPEG_OUTPUT = 64 * 1024

_HARDWARE_ENCODERS = ["h264_nvenc", "h264_qsv", "h264_amf", "h264_videotoolbox"]


@dataclass
class ABRProfile:
    """One ABR rendition of the transcoding ladder."""

    name: str
    width: int
    height: int
    bitrate: int  # bits per second
    frame_rate: int
    audio_bitrate: int  # bits per second


@dataclass
class TranscoderConfig:
    worker_count: int = 2
    ffmpeg_path: str = "ffmpeg"
    gpu_enabled: bool = False
    output_format: str = "hls"
    abr_ladder: list[ABRProfile] = field(
        default_factory=lambda: [
            ABRProfile("1080p", 1920, 1080, 5_000_000, 30, 192_000),
            ABRProfile("720p", 1280, 720, 3_000_000, 30, 128_000),
            ABRProfile("480p", 854, 480, 1_500_000, 30, 96_000),
            ABRProfile("360p", 640, 360, 800_000, 30, 64_000),
        ]
    )


@dataclass
class TranscodeJob:
    id: str
    input_path: str
    output_dir: str
    stream_id: str
    profiles: list[ABRProfile] = field(default_factory=list)
    on_complete: Optional[Callable[[Optional[Exception]], None]] = None


@dataclass
class WorkerStats:
    start_time: float = 0.0
    bytes_processed: int = 0
    frames_encoded: int = 0
    errors: int = 0
    jobs_completed: int = 0


@dataclass
class HardwareInfo:
    ffmpeg_path: str = ""
    selected_encoder: str = "libx264"
    hardware_encoders: list[str] = field(default_factory=list)


class _BoundedBuffer:
    """Bounded byte buffer for capturing limited FFmpeg progress output."""

    def __init__(self, limit: int = _MAX_FFMPEG_OUTPUT) -> None:
        self._lock = threading.Lock()
        self._data = bytearray()
        self._limit = limit

    def write(self, data: bytes) -> int:
        with self._lock:
            original = len(data)
            remaining = self._limit - len(self._data)
            if remaining > 0:
                if len(data) > remaining:
                    data = data[:remaining]
                self._data.extend(data)
            return original

    def string(self) -> str:
        with self._lock:
            return bytes(self._data).decode("utf-8", errors="replace")


class Worker:
    """A single transcoder worker that pulls jobs from a queue."""

    def __init__(
        self,
        worker_id: int,
        config: TranscoderConfig,
        encoder: str,
    ) -> None:
        self.id = worker_id
        self.config = config
        self.encoder = encoder
        self._lock = threading.Lock()
        self._cmd: Optional[subprocess.Popen] = None
        self.running = False
        self.stats = WorkerStats()

    def process_jobs(
        self,
        ctx: "threading.Event",
        jobs,
    ) -> None:
        while not ctx.is_set():
            try:
                job = jobs.get(timeout=0.2)
            except queue.Empty:  # nothing to do yet
                continue
            if job is None:
                continue
            if ctx.is_set():
                self._call_completion(job, contextlib.suppress)  # type: ignore[arg-type]
                return
            self._execute_job(ctx, job)

    def _execute_job(  # noqa: C901 - complex FFmpeg job execution with retries
        self, ctx: "threading.Event", job: TranscodeJob
    ) -> None:
        with self._lock:
            self.running = True
            self.stats.start_time = time.time()

        try:
            output_dir = self._prepare_output_dir(job.output_dir)
            job.output_dir = output_dir

            profiles = job.profiles or self.config.abr_ladder
            for profile in profiles:
                if ctx.is_set():
                    self._finish_job(job, InterruptedError())
                    return
                args = self._build_ffmpeg_args(job, profile)
                cmd = subprocess.Popen(  # nosec B603
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                with self._lock:
                    self._cmd = cmd
                progress_buf = _BoundedBuffer()
                stderr_buf = _BoundedBuffer()

                def _pump(src, dst):
                    try:
                        for chunk in iter(lambda: src.read(65536), b""):
                            dst.write(chunk)
                    except Exception:  # noqa: BLE001 - pump thread must not crash
                        _LOG.debug("ffmpeg output pump stopped", exc_info=True)

                t1 = threading.Thread(target=_pump, args=(cmd.stdout, progress_buf), daemon=True)
                t2 = threading.Thread(target=_pump, args=(cmd.stderr, stderr_buf), daemon=True)
                t1.start()
                t2.start()
                cmd.wait()
                t1.join(timeout=5)
                t2.join(timeout=5)

                self._record_progress(job, progress_buf.string())

                if ctx.is_set():
                    self._finish_job(job, InterruptedError())
                    return
                err: Optional[Exception] = None
                # Check returncode
                if cmd.returncode != 0:
                    err = subprocess.CalledProcessError(
                        cmd.returncode or 1, args, stderr_buf.string()
                    )
                if err is None:
                    out_path = self._transcoded_output_path(job, profile)
                    try:
                        info = os.stat(out_path)
                        if (
                            os.path.islink(out_path)
                            or not os.path.isfile(out_path)
                            or info.st_size == 0
                        ):
                            err = TranscoderError("transcoding output is empty")
                    except OSError:
                        err = TranscoderError("transcoding output was not created")
                if err is not None:
                    self._logger_error(
                        "transcoding profile failed",
                        job_id=job.id,
                        profile=profile.name,
                        error=str(err),
                        ffmpeg_output=stderr_buf.string(),
                    )
                    self._finish_job(job, err)
                    return
        except Exception as exc:  # noqa: BLE001
            self._finish_job(job, exc)
            return

        with self._lock:
            self.stats.jobs_completed += 1
        self._call_completion(job, None)

    def _finish_job(self, job: TranscodeJob, err: Optional[Exception]) -> None:
        if err is not None and not isinstance(err, InterruptedError):
            with self._lock:
                self.stats.errors += 1
        with self._lock:
            self.running = False
            self._cmd = None
        self._call_completion(job, err)

    def _build_ffmpeg_args(self, job: TranscodeJob, profile: ABRProfile) -> list[str]:
        output = self._transcoded_output_path(job, profile)
        video_filter = (
            f"scale={profile.width}:{profile.height}:force_original_aspect_ratio=decrease,"
            f"pad={profile.width}:{profile.height}:(ow-iw)/2:(oh-ih)/2,fps={profile.frame_rate}"
        )
        bitrate = str(profile.bitrate)
        bufsize = str(profile.bitrate * 2)
        args = [
            "-hide_banner",
            "-loglevel",
            "warning",
            "-nostdin",
            "-nostats",
            "-progress",
            "pipe:1",
            "-y",
            "-i",
            job.input_path,
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            video_filter,
            "-c:v",
            self.encoder,
        ]
        if self.encoder == "libx264":
            args.extend(["-preset", "fast"])
        args.extend(
            [
                "-b:v",
                bitrate,
                "-maxrate",
                bitrate,
                "-bufsize",
                bufsize,
                "-g",
                str(profile.frame_rate * 2),
                "-sc_threshold",
                "0",
                "-c:a",
                "aac",
                "-b:a",
                str(profile.audio_bitrate),
                "-f",
                "hls",
                "-hls_time",
                "2",
                "-hls_list_size",
                "6",
                "-hls_flags",
                "delete_segments+independent_segments",
                output,
            ]
        )
        return args

    @staticmethod
    def _transcoded_output_path(job: TranscodeJob, profile: ABRProfile) -> str:
        return str(Path(job.output_dir) / f"{job.stream_id}_{profile.name}.m3u8")

    def _prepare_output_dir(self, path: str) -> str:
        path = path.strip()
        path_slash = path.replace("\\", "/")
        if (
            "/../" in path_slash
            or path_slash.startswith("../")
            or path_slash.endswith("/..")
            or path_slash == ".."
        ):
            raise InvalidJobError("output directory contains a traversal segment")
        abs_path = str(Path(path).resolve())
        if abs_path == os.sep:
            raise InvalidJobError("output directory is unsafe")
        Path(abs_path).mkdir(parents=True, exist_ok=True)
        info = Path(abs_path)
        if info.is_symlink() or not info.is_dir():
            raise InvalidJobError("output directory must be a regular directory")
        return abs_path

    def _record_progress(self, job: TranscodeJob, progress: str) -> None:
        frames, bytes_processed = self._parse_progress(progress)
        if bytes_processed == 0:
            try:
                info = os.stat(job.input_path)
                if os.path.isfile(job.input_path):
                    bytes_processed = info.st_size
            except OSError:
                pass
        with self._lock:
            self.stats.bytes_processed += bytes_processed
            self.stats.frames_encoded += frames

    @staticmethod
    def _parse_progress(progress: str) -> tuple[int, int]:
        frames = 0
        bytes_processed = 0
        for line in progress.split("\n"):
            line = line.strip()
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            try:
                parsed = int(value.strip())
            except ValueError:
                continue
            if parsed < 0:
                continue
            if key == "frame":
                frames = parsed
            elif key == "total_size":
                bytes_processed = parsed
        return frames, bytes_processed

    def _call_completion(self, job: TranscodeJob, err: Optional[Exception]) -> None:
        if job is None or job.on_complete is None:
            return
        try:
            job.on_complete(err)
        except Exception:  # noqa: BLE001 - a callback must not stop the worker
            _LOG.warning("transcode completion callback failed", exc_info=True)

    def _logger_error(
        self,
        msg: str,
        job_id: str,
        profile: str,
        error: str,
        ffmpeg_output: str,
    ) -> None:
        # Placeholder for injected logging.
        pass

    def get_stats(self) -> WorkerStats:
        with self._lock:
            return WorkerStats(
                start_time=self.stats.start_time,
                bytes_processed=self.stats.bytes_processed,
                frames_encoded=self.stats.frames_encoded,
                errors=self.stats.errors,
                jobs_completed=self.stats.jobs_completed,
            )

    def is_running(self) -> bool:
        with self._lock:
            return self.running


class Manager:
    """Transcoder manager with a worker pool."""

    def __init__(
        self,
        config: TranscoderConfig,
    ) -> None:
        if config.worker_count <= 0 or config.worker_count > _MAX_TRANSCODER_WORKERS:
            raise TranscoderError(f"worker count must be between 1 and {_MAX_TRANSCODER_WORKERS}")
        if not config.ffmpeg_path:
            config.ffmpeg_path = "ffmpeg"
        if config.output_format != "hls":
            raise TranscoderError(f"unsupported transcoder output format {config.output_format!r}")
        if not config.abr_ladder:
            raise TranscoderError("transcoder ABR ladder cannot be empty")
        config.abr_ladder = [ABRProfile(**vars(p)) for p in config.abr_ladder]
        for profile in config.abr_ladder:
            self._validate_profile(profile)
        self._validate_profiles(config.abr_ladder)

        resolved = shutil.which(config.ffmpeg_path)
        if resolved is None:
            raise TranscoderError(f"ffmpeg not found at {config.ffmpeg_path!r}")
        config.ffmpeg_path = resolved

        hardware = self._detect_hardware(resolved)
        encoder = "libx264"
        if config.gpu_enabled and hardware.hardware_encoders:
            encoder = hardware.hardware_encoders[0]

        self._config = config
        self._workers = [Worker(i, config, encoder) for i in range(config.worker_count)]
        self._jobs: list[TranscodeJob] = []
        self._jobs_lock = threading.Lock()
        self._ctx_event = threading.Event()
        self._wg = threading.WaitGroup() if hasattr(threading, "WaitGroup") else None
        self._threads: list[threading.Thread] = []
        self._job_ids: set[str] = set()
        self._stream_ids: set[str] = set()
        self._started = False
        self._stopped = False
        self._encoder = encoder
        self._logger = None  # placeholder

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self) -> None:
        with self._jobs_lock:
            if self._stopped:
                raise ManagerStoppedError("transcoder manager is stopped")
            if self._started:
                return
            self._started = True
        self._ctx_event.clear()
        for worker in self._workers:
            t = threading.Thread(
                target=worker.process_jobs,
                args=(self._ctx_event, self._job_queue),
                daemon=True,
            )
            t.start()
            self._threads.append(t)
        if self._logger:
            self._logger.info(
                "transcoder initialized",
                extra={"workers": len(self._workers), "encoder": self._encoder},
            )

    @property
    def _job_queue(self):
        # Simple list-based queue protected by _jobs_lock.
        return self._jobs

    def stop(self, timeout: float = 15.0) -> None:
        with self._jobs_lock:
            if not self._stopped:
                self._stopped = True
                self._ctx_event.set()
        deadline = time.time() + timeout
        while True:
            with self._jobs_lock:
                active = any(w.is_running() for w in self._workers)
            if not active:
                break
            if time.time() >= deadline:
                raise TranscoderError("timeout waiting for transcoder workers to stop")
            time.sleep(0.2)
        self._cancel_queued_jobs()

    def submit(self, job: TranscodeJob) -> None:
        copy_job = self._prepare_job(job)
        original_callback = copy_job.on_complete
        copy_job.on_complete = lambda err: self._wrapped_complete(copy_job, original_callback, err)
        self._register_job(copy_job)
        if self._logger:
            self._logger.info(
                "transcoding job submitted",
                extra={"job_id": copy_job.id, "stream_id": copy_job.stream_id},
            )

    def _prepare_job(self, job: TranscodeJob) -> TranscodeJob:
        if not self._validate_job(job):
            raise InvalidJobError("invalid job")
        copy_job = TranscodeJob(
            id=job.id,
            input_path=job.input_path,
            output_dir=job.output_dir,
            stream_id=job.stream_id,
            profiles=[ABRProfile(**vars(p)) for p in job.profiles],
            on_complete=job.on_complete,
        )
        if not copy_job.profiles:
            copy_job.profiles = [ABRProfile(**vars(p)) for p in self._config.abr_ladder]
        for profile in copy_job.profiles:
            self._validate_profile(profile)
        self._validate_profiles(copy_job.profiles)
        return copy_job

    def _wrapped_complete(
        self,
        job: TranscodeJob,
        original: Optional[Callable[[Optional[Exception]], None]],
        err: Optional[Exception],
    ) -> None:
        self._complete_job(job.id, job.stream_id)
        if original is not None:
            original(err)

    def _register_job(self, job: TranscodeJob) -> None:
        with self._jobs_lock:
            if not self._started:
                raise ManagerNotStartedError("transcoder manager is not started")
            if self._stopped:
                raise ManagerStoppedError("transcoder manager is stopped")
            if job.id in self._job_ids:
                raise DuplicateJobError("transcoding job already exists")
            if job.stream_id in self._stream_ids:
                raise StreamBusyError("stream already has a transcoding job")
            self._job_ids.add(job.id)
            self._stream_ids.add(job.stream_id)
            self._jobs.append(job)

    def get_stats(self) -> dict:
        with self._jobs_lock:
            queue_size = len(self._jobs)
            worker_count = len(self._workers)
            encoder = self._encoder
        total = WorkerStats()
        active_workers = 0
        for worker in self._workers:
            ws = worker.get_stats()
            total.bytes_processed += ws.bytes_processed
            total.frames_encoded += ws.frames_encoded
            total.errors += ws.errors
            total.jobs_completed += ws.jobs_completed
            if worker.is_running():
                active_workers += 1
        return {
            "worker_count": worker_count,
            "active_workers": active_workers,
            "queue_size": queue_size,
            "encoder": encoder,
            "bytes_processed": total.bytes_processed,
            "frames_encoded": total.frames_encoded,
            "jobs_completed": total.jobs_completed,
            "errors": total.errors,
        }

    def get_encoder(self) -> str:
        return self._encoder

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _complete_job(self, job_id: str, stream_id: str) -> None:
        with self._jobs_lock:
            self._job_ids.discard(job_id)
            self._stream_ids.discard(stream_id)

    def _cancel_queued_jobs(self) -> None:
        queued: list[TranscodeJob] = []
        with self._jobs_lock:
            self._jobs, queued = [], self._jobs
        for job in queued:
            self._call_canceled(job)

    def _call_canceled(self, job: TranscodeJob) -> None:
        if job is None or job.on_complete is None:
            return
        try:
            job.on_complete(InterruptedError())
        except Exception:  # noqa: BLE001 - a callback must not stop the worker
            _LOG.warning("transcode cancel callback failed", exc_info=True)

    @staticmethod
    def _detect_hardware(ffmpeg_path: str) -> HardwareInfo:
        info = HardwareInfo(ffmpeg_path=ffmpeg_path)
        try:
            proc = subprocess.run(  # nosec B603
                [ffmpeg_path, "-hide_banner", "-nostdin", "-encoders"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            text = proc.stdout + "\n" + proc.stderr
        except Exception:
            return info
        for encoder in _HARDWARE_ENCODERS:
            if encoder in text:
                info.hardware_encoders.append(encoder)
        if info.hardware_encoders:
            info.selected_encoder = info.hardware_encoders[0]
        return info

    @staticmethod
    def _validate_job(job: TranscodeJob) -> bool:
        if job is None or not job.id or len(job.id) > 128:
            raise InvalidJobError("invalid job id")
        if not job.input_path or job.input_path != job.input_path.strip():
            raise InvalidJobError("invalid input path")
        if any(ch in job.input_path for ch in ("\x00", "\r", "\n", "\t")):
            raise InvalidJobError("invalid input path")
        try:
            validate_stream_id(job.stream_id)
        except Exception as exc:
            raise InvalidJobError(str(exc)) from exc
        if not job.output_dir or job.output_dir != job.output_dir.strip():
            raise InvalidJobError("invalid output dir")
        if any(ch in job.output_dir for ch in ("\x00", "\r", "\n", "\t")):
            raise InvalidJobError("invalid output dir")
        return True

    @staticmethod
    def _validate_profile(profile: ABRProfile) -> None:
        name = profile.name
        if not name or len(name) > 128:
            raise TranscoderError(f"invalid ABR profile {name!r}")
        if not (name[0].isalnum() and all(ch.isalnum() or ch in ("-", "_", ".") for ch in name)):
            raise TranscoderError(f"invalid ABR profile {name!r}")
        if not (
            0 < profile.width <= _MAX_TRANSCODER_DIMENSION
            and 0 < profile.height <= _MAX_TRANSCODER_DIMENSION
            and 0 < profile.bitrate <= _MAX_TRANSCODER_BITRATE
            and 0 < profile.frame_rate <= _MAX_TRANSCODER_FRAME_RATE
            and 0 < profile.audio_bitrate <= _MAX_TRANSCODER_AUDIO_BITRATE
        ):
            raise TranscoderError(f"invalid ABR profile {name!r}")

    @staticmethod
    def _validate_profiles(profiles: list[ABRProfile]) -> None:
        seen: set[str] = set()
        for profile in profiles:
            if profile.name in seen:
                raise TranscoderError(f"duplicate ABR profile {profile.name!r}")
            seen.add(profile.name)
