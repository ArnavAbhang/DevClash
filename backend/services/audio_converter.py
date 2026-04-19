"""
audio_converter.py
~~~~~~~~~~~~~~~~~~
Converts audio files to WAV (PCM 16-bit, 16 kHz mono) using FFmpeg.

The conversion runs in a subprocess via asyncio so it never blocks the
FastAPI event loop, and works efficiently for large files by streaming
through stdin/stdout rather than writing intermediate files to disk.

FFmpeg command used
-------------------
    ffmpeg -y \\
        -i pipe:0 \\
        -ar 16000 \\
        -ac 1 \\
        -sample_fmt s16 \\
        -f wav \\
        pipe:1

Flags explained:
  -y            Overwrite output without prompting (required for pipe output).
  -i pipe:0     Read input from stdin.
  -ar 16000     Resample to 16 kHz — the sweet spot for most ASR models.
  -ac 1         Downmix to mono.
  -sample_fmt s16  16-bit signed PCM — universally supported WAV variant.
  -f wav        Force WAV container on stdout.
  pipe:1        Write output to stdout.

FFmpeg auto-detects the input format from the bitstream, so no explicit
-f flag is needed on the input side.

Why shutil.which("ffmpeg") fails on Windows with WinGet
--------------------------------------------------------
WinGet installs FFmpeg into a per-package path under:
  %LOCALAPPDATA%\\Microsoft\\WinGet\\Packages\\Gyan.FFmpeg_...\\...\\bin\\

It adds this directory to the *User* PATH in the Windows Registry.  That
registry change is only visible to processes whose environment was inherited
from an interactive shell that was started *after* the WinGet install.

When uvicorn is launched from a terminal that was opened before the install,
or from a service / IDE process, os.environ['PATH'] does not contain the
WinGet bin directory.  shutil.which("ffmpeg") searches only os.environ['PATH']
and therefore returns None — even though `ffmpeg -version` works fine in a
fresh CMD window.

The fix
-------
_ffmpeg_path() uses a three-step resolution strategy:

  1. FFMPEG_PATH env var — explicit override, highest priority.
     Set this in backend/.env for a guaranteed, portable solution.

  2. shutil.which("ffmpeg") — works when PATH is correct (Linux, macOS,
     properly configured Windows sessions).

  3. Windows fallback scan — reads the User PATH directly from the Windows
     Registry (HKCU\\Environment) and searches those directories.  This
     catches the WinGet case where the registry is up to date but the
     running process's PATH is stale.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

#: MIME type produced by this converter.
OUTPUT_MIME_TYPE = "audio/wav"

#: Set of MIME types (base, codec-stripped) that need conversion.
#: WAV and MP3 are already accepted natively by the ASR service.
NEEDS_CONVERSION: frozenset[str] = frozenset(
    {
        "audio/webm",
        "audio/ogg",
        "audio/mp4",
        "audio/x-m4a",
        "audio/aac",
        "audio/flac",
        "audio/x-flac",
        "audio/opus",
    }
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_FFMPEG_ARGS = [
    "-y",            # overwrite output (required for pipe:1)
    "-i", "pipe:0",  # read from stdin
    "-ar", "16000",  # 16 kHz sample rate
    "-ac", "1",      # mono
    "-sample_fmt", "s16",  # 16-bit PCM
    "-f", "wav",     # WAV container
    "pipe:1",        # write to stdout
]

# Suppress FFmpeg's verbose banner and progress output so logs stay clean.
_FFMPEG_QUIET = ["-loglevel", "error", "-nostats"]

# Cache the resolved path so we only search once per process lifetime.
_resolved_ffmpeg_path: Optional[str] = None


def _read_registry_user_path() -> list[str]:
    """
    Read the User PATH from the Windows Registry.

    Returns an empty list on non-Windows platforms or if the registry key
    cannot be opened (e.g. insufficient permissions).

    This is the key fix for the WinGet PATH problem: WinGet writes the
    FFmpeg bin directory to HKCU\\Environment\\Path in the registry, but
    the running process's os.environ['PATH'] may be stale (set before the
    WinGet install or before the registry change was propagated).
    """
    if sys.platform != "win32":
        return []
    try:
        import winreg  # only available on Windows
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
        try:
            value, _ = winreg.QueryValueEx(key, "Path")
            return [p.strip() for p in value.split(";") if p.strip()]
        finally:
            winreg.CloseKey(key)
    except Exception:
        return []


def _which_in_dirs(name: str, dirs: list[str]) -> Optional[str]:
    """Search *dirs* for an executable named *name* (with .exe on Windows)."""
    exts = [".exe", ".cmd", ".bat", ""] if sys.platform == "win32" else [""]
    for directory in dirs:
        for ext in exts:
            candidate = Path(directory) / f"{name}{ext}"
            if candidate.is_file():
                return str(candidate)
    return None


def _ffmpeg_path() -> str:
    """
    Resolve the ffmpeg binary path using a three-step strategy.

    Resolution order (first match wins):
      1. FFMPEG_PATH environment variable — explicit override.
      2. shutil.which("ffmpeg") — standard PATH search.
      3. Windows Registry User PATH scan — catches stale-PATH WinGet installs.

    Raises RuntimeError with a clear message if ffmpeg cannot be found.
    """
    global _resolved_ffmpeg_path
    if _resolved_ffmpeg_path is not None:
        return _resolved_ffmpeg_path

    # ── Step 1: explicit env var override ────────────────────────────────────
    explicit = os.environ.get("FFMPEG_PATH", "").strip()
    if explicit:
        p = Path(explicit)
        if p.is_file():
            _resolved_ffmpeg_path = str(p)
            return _resolved_ffmpeg_path
        # Env var set but path doesn't exist — warn and fall through.
        import warnings
        warnings.warn(
            f"FFMPEG_PATH is set to '{explicit}' but that file does not exist. "
            "Falling back to PATH search.",
            stacklevel=2,
        )

    # ── Step 2: standard PATH search ─────────────────────────────────────────
    found = shutil.which("ffmpeg")
    if found:
        _resolved_ffmpeg_path = found
        return _resolved_ffmpeg_path

    # ── Step 3: Windows Registry User PATH scan ───────────────────────────────
    # Handles the WinGet case where the registry PATH is up to date but the
    # process's os.environ['PATH'] is stale.
    registry_dirs = _read_registry_user_path()
    if registry_dirs:
        found = _which_in_dirs("ffmpeg", registry_dirs)
        if found:
            _resolved_ffmpeg_path = found
            return _resolved_ffmpeg_path

    # ── Not found anywhere ────────────────────────────────────────────────────
    raise RuntimeError(
        "FFmpeg is not installed or not on PATH.\n"
        "\n"
        "Quick fix — add this to backend/.env:\n"
        "  FFMPEG_PATH=C:\\Users\\admin\\AppData\\Local\\Microsoft\\WinGet\\"
        "Packages\\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\\"
        "ffmpeg-8.1-full_build\\bin\\ffmpeg.exe\n"
        "\n"
        "Or install FFmpeg system-wide:\n"
        "  Windows (winget): winget install --id Gyan.FFmpeg\n"
        "  macOS (brew):     brew install ffmpeg\n"
        "  Ubuntu/Debian:    sudo apt install ffmpeg\n"
        "\n"
        "After a WinGet install, restart your terminal so PATH is refreshed."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def to_wav(audio_bytes: bytes) -> bytes:
    """Convert *audio_bytes* (any FFmpeg-supported format) to WAV bytes.

    The conversion runs asynchronously via ``asyncio.create_subprocess_exec``
    so the FastAPI event loop is never blocked.

    Args:
        audio_bytes: Raw audio data in any format FFmpeg can decode.

    Returns:
        WAV-encoded bytes (PCM 16-bit, 16 kHz, mono).

    Raises:
        RuntimeError: If FFmpeg is not installed, or if the conversion fails
                      (e.g. the input is corrupt or not a valid audio file).
    """
    ffmpeg = _ffmpeg_path()

    proc = await asyncio.create_subprocess_exec(
        ffmpeg,
        *_FFMPEG_QUIET,
        *_FFMPEG_ARGS,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    wav_bytes, stderr_output = await proc.communicate(input=audio_bytes)

    if proc.returncode != 0:
        error_detail = stderr_output.decode(errors="replace").strip()
        raise RuntimeError(
            f"FFmpeg conversion failed (exit {proc.returncode}): {error_detail}"
        )

    if not wav_bytes:
        raise RuntimeError(
            "FFmpeg produced no output — the input may be corrupt or empty."
        )

    return wav_bytes


def needs_conversion(base_mime: str) -> bool:
    """Return True if *base_mime* requires FFmpeg conversion before transcription."""
    return base_mime in NEEDS_CONVERSION
