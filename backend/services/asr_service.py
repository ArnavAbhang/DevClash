"""
asr_service.py
~~~~~~~~~~~~~~
HTTP client for the Parakeet ASR API.

SSL / certificate handling
--------------------------
httpx.AsyncClient() defaults to verifying TLS certificates against the
certifi CA bundle — a curated set of *public* certificate authorities.
This is correct for production endpoints (e.g. api.parakit.io) but fails
with a CERTIFICATE_VERIFY_FAILED error when Parakeet is running locally
with a self-signed certificate, because certifi has no knowledge of that
certificate.

Root cause of SSL: CERTIFICATE_VERIFY_FAILED
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  1. certifi ships its own CA bundle and does NOT read the Windows
     Certificate Store.  Even if you added the self-signed cert to
     Windows' Trusted Root CAs, httpx/certifi won't see it.

  2. httpx.AsyncClient() with no arguments uses certifi by default.
     The self-signed cert is not in certifi → verification fails.

  3. The wrong fix is verify=False — that disables all TLS verification
     and exposes the connection to man-in-the-middle attacks.

The correct production-safe fix
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Export the Parakeet server's certificate (or its signing CA) as a PEM
file and set PARAKIT_CA_BUNDLE in backend/.env to that file's path.
httpx will then verify the server's certificate against your custom CA
instead of certifi, giving you full TLS verification with zero security
compromise.

How to export the certificate (Windows)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Option A — from a browser:
  1. Open the Parakeet HTTPS URL in Chrome/Edge.
  2. Click the padlock → Certificate → Details → Copy to File.
  3. Export as "Base-64 encoded X.509 (.CER)" → save as parakeet-ca.pem.
  4. Set PARAKIT_CA_BUNDLE=C:\\path\\to\\parakeet-ca.pem in backend/.env.

Option B — from PowerShell (if you know the hostname):
  $cert = [System.Net.ServicePointManager]::ServerCertificateValidationCallback
  # or use openssl:
  openssl s_client -connect localhost:8080 -showcerts </dev/null 2>/dev/null \\
    | openssl x509 -outform PEM > parakeet-ca.pem

Option C — Windows Certificate Store (if cert is already trusted there):
  Set PARAKIT_CA_BUNDLE=WINDOWS to use the Windows system cert store
  instead of certifi.  This works if the self-signed cert was added to
  Trusted Root Certification Authorities via certmgr.msc.

Environment variables
~~~~~~~~~~~~~~~~~~~~~
  PARAKIT_API_KEY      — Bearer token for the ASR API (required)
  PARAKIT_API_ENDPOINT — Full HTTPS URL of the transcribe endpoint (required)
  PARAKIT_CA_BUNDLE    — One of:
                           (empty)   → use certifi (default, for public endpoints)
                           <path>    → path to a PEM file or directory with CA certs
                           WINDOWS   → use the Windows system certificate store
"""

import os
import ssl
import sys
from pathlib import Path
from typing import Optional, Union

import certifi
import httpx
from dotenv import load_dotenv

load_dotenv()

# Module-level constants — read once at import time.
# Also validated at call time so monkeypatching works in tests.
PARAKIT_API_KEY: Optional[str] = os.getenv("PARAKIT_API_KEY")
PARAKIT_API_ENDPOINT: Optional[str] = os.getenv("PARAKIT_API_ENDPOINT")

if not PARAKIT_API_KEY:
    raise ValueError("PARAKIT_API_KEY is not set")


# ---------------------------------------------------------------------------
# SSL context builder
# ---------------------------------------------------------------------------

def _build_ssl_context() -> Union[ssl.SSLContext, bool, str]:
    """
    Build the SSL verification argument for httpx.AsyncClient(verify=...).

    Returns one of:
      - ssl.SSLContext  — custom context with the self-signed CA loaded
      - str             — path to a PEM CA bundle file (certifi default)
      - True            — httpx default (certifi), returned when no override set

    Never returns False — disabling verification is not a safe option.
    """
    ca_bundle = os.getenv("PARAKIT_CA_BUNDLE", "").strip()

    # ── No override: use certifi (correct for public HTTPS endpoints) ─────────
    if not ca_bundle:
        return True  # httpx default → certifi

    # ── Special value "WINDOWS": use the Windows system certificate store ─────
    # Useful when the self-signed cert has been added to Windows'
    # Trusted Root Certification Authorities via certmgr.msc.
    if ca_bundle.upper() == "WINDOWS":
        if sys.platform != "win32":
            import warnings
            warnings.warn(
                "PARAKIT_CA_BUNDLE=WINDOWS is only supported on Windows. "
                "Falling back to certifi.",
                stacklevel=2,
            )
            return True
        # ssl.create_default_context() on Windows automatically loads from
        # the Windows Certificate Store (via the CNG/SChannel backend).
        ctx = ssl.create_default_context()
        return ctx

    # ── Custom PEM file or directory ──────────────────────────────────────────
    bundle_path = Path(ca_bundle)
    if not bundle_path.exists():
        raise FileNotFoundError(
            f"PARAKIT_CA_BUNDLE is set to '{ca_bundle}' but that path does not exist.\n"
            "Export the Parakeet server certificate as a PEM file and set the path "
            "in backend/.env, or remove PARAKIT_CA_BUNDLE to use the certifi default."
        )

    if bundle_path.is_dir():
        # httpx accepts a directory of PEM files (like /etc/ssl/certs on Linux).
        ctx = ssl.create_default_context(capath=str(bundle_path))
    else:
        # Single PEM file — the most common case for a self-signed cert.
        ctx = ssl.create_default_context(cafile=str(bundle_path))

    return ctx


# Build once at module load time so the file is validated on startup,
# not on the first request.
_SSL_VERIFY = _build_ssl_context()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def transcribe(audio_bytes: bytes, mime_type: str) -> str:
    """Send audio bytes to the Parakeet ASR API and return the transcription.

    Args:
        audio_bytes: Raw audio data to transcribe.
        mime_type:   MIME type of the audio (e.g. "audio/wav" or "audio/mpeg").

    Returns:
        The transcription string extracted from the Parakeet API response.

    Raises:
        ValueError:  If PARAKIT_API_KEY is absent.
        RuntimeError: If the Parakeet API returns an HTTP error or is unreachable.
    """
    # Re-read from env at call time so monkeypatching works in tests.
    api_key = os.getenv("PARAKIT_API_KEY") or PARAKIT_API_KEY
    endpoint = os.getenv("PARAKIT_API_ENDPOINT") or PARAKIT_API_ENDPOINT

    print(f"[DEBUG] ASR: api_key present: {bool(api_key)}, endpoint: {endpoint}")

    if not api_key:
        raise ValueError("PARAKIT_API_KEY is not set")

    headers = {"Authorization": f"Bearer {api_key}"}

    print(f"[DEBUG] ASR: Sending request to {endpoint}, mime_type: {mime_type}, audio_size: {len(audio_bytes)} bytes")

    # _SSL_VERIFY is one of:
    #   True            → httpx uses certifi (public endpoints)
    #   ssl.SSLContext  → custom CA (self-signed cert or Windows store)
    #   str             → path to PEM bundle (not currently returned but
    #                     supported by httpx for forward compatibility)
    async with httpx.AsyncClient(verify=_SSL_VERIFY, timeout=30.0) as client:
        try:
            response = await client.post(
                endpoint,
                headers=headers,
                files={
                    "audio": ("audio", audio_bytes, mime_type),
                },
                data={"mime_type": mime_type},
            )
            print(f"[DEBUG] ASR: Response status: {response.status_code}")
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] ASR: HTTP error {e.response.status_code}: {e.response.text}")
            raise RuntimeError(
                f"Parakit API error {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.ConnectError as e:
            # Separate SSL errors from general connectivity errors so the
            # caller gets a more actionable message.
            msg = str(e)
            if "CERTIFICATE_VERIFY_FAILED" in msg or "SSL" in msg.upper():
                print(f"[ERROR] ASR: SSL error: {e}")
                raise RuntimeError(
                    f"SSL certificate verification failed for Parakeet endpoint.\n"
                    f"Original error: {e}\n\n"
                    "To fix this:\n"
                    "  1. Export the Parakeet server certificate as a PEM file.\n"
                    "  2. Set PARAKIT_CA_BUNDLE=/path/to/parakeet-ca.pem in backend/.env.\n"
                    "  3. Or set PARAKIT_CA_BUNDLE=WINDOWS to use the Windows cert store\n"
                    "     (requires the cert to be in Trusted Root CAs via certmgr.msc).\n"
                    "See backend/services/asr_service.py for full instructions."
                ) from e
            print(f"[ERROR] ASR: Connect error: {e}")
            raise RuntimeError(f"ASR service unreachable: {e}") from e
        except httpx.RequestError as e:
            print(f"[ERROR] ASR: Request error: {e}")
            raise RuntimeError(f"ASR service unreachable: {e}") from e

    result = response.json()
    transcription = result.get("transcription", "")
    print(f"[DEBUG] ASR: Full response: {result}, extracted transcription: '{transcription}'")

    return transcription
