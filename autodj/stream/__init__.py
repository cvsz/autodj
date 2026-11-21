"""Multi-platform stream infrastructure for AutoDJ.

Ported design patterns from cvsz/streamdbc (Go) adapted to Python:

- Stream/room registry with thread-safe lifecycle (IDLE, LIVE, RECORDING, ERROR)
- Stream-scoped auth with JWT tokens and API keys
- FFmpeg-based recorder and transcoder managers with context cancellation
- Safe stream/room identifier validation
- Platform adapters (Camfrog, YouTube, TikTok, Facebook) via probe accounts
- Adapter manager that routes messages through AutoDJ's command system

AutoDJ uses this to track active streams across platforms and manage
per-stream audio output and recording.
"""

from __future__ import annotations

from .adapter_manager import AdapterManager
from .adapters.base import (
    AdapterError,
    AdapterState,
    ChatMessage,
    StreamAdapter,
)
from .adapters.camfrog import CamfrogAdapter
from .adapters.composite import CompositeStreamAdapter
from .adapters.facebook import FacebookAdapter
from .adapters.tiktok import TikTokAdapter
from .adapters.youtube import YouTubeAdapter
from .auth import (
    APIKeyValidator,
    AuthError,
    AuthManager,
    Claims,
    ExpiredTokenError,
    InvalidTokenError,
    UnauthorizedError,
    authorize,
)
from .probe_account import ProbeAccount, ProbeAccountStore
from .probe_login import ProbeAccountLoginUI, ProbeLoginError, ProbeLoginManager
from .recorder import (
    RecorderError,
    RecorderManager,
    RecorderStoppedError,
    Recording,
)
from .registry import (
    StreamError,
    StreamInfo,
    StreamRegistry,
    StreamState,
)
from .stream_id import (
    StreamIDError,
    validate_stream_id,
    validate_stream_name,
)
from .transcoder import (
    ABRProfile,
    DuplicateJobError,
    InvalidJobError,
    Manager,
    ManagerNotStartedError,
    ManagerStoppedError,
    StreamBusyError,
    TranscodeJob,
    TranscoderConfig,
    TranscoderError,
    Worker,
    WorkerStats,
)

__all__ = [
    # Registry
    "StreamState",
    "StreamInfo",
    "StreamRegistry",
    "StreamError",
    # Auth
    "AuthManager",
    "APIKeyValidator",
    "Claims",
    "AuthError",
    "InvalidTokenError",
    "ExpiredTokenError",
    "UnauthorizedError",
    "authorize",
    # Probe Account
    "ProbeAccount",
    "ProbeAccountStore",
    "ProbeLoginManager",
    "ProbeLoginError",
    "ProbeAccountLoginUI",
    # Recorder
    "RecorderManager",
    "Recording",
    "RecorderError",
    "RecorderStoppedError",
    # Transcoder
    "TranscoderConfig",
    "ABRProfile",
    "TranscodeJob",
    "Manager",
    "Worker",
    "WorkerStats",
    "TranscoderError",
    "ManagerNotStartedError",
    "ManagerStoppedError",
    "DuplicateJobError",
    "StreamBusyError",
    "InvalidJobError",
    # Stream ID
    "StreamIDError",
    "validate_stream_id",
    "validate_stream_name",
    # Adapters
    "StreamAdapter",
    "ChatMessage",
    "AdapterState",
    "AdapterError",
    "CamfrogAdapter",
    "YouTubeAdapter",
    "TikTokAdapter",
    "FacebookAdapter",
    "CompositeStreamAdapter",
    # Manager
    "AdapterManager",
]
