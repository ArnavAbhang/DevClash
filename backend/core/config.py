"""
core/config.py
~~~~~~~~~~~~~~
Single source of truth for all environment variables.
Replaces the scattered process.env calls across the Node.js codebase.
"""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── Server ────────────────────────────────────────────────────────────────
    environment: str = os.getenv("ENVIRONMENT", "development")
    client_origin: str = os.getenv("CLIENT_ORIGIN", "http://localhost:3000")
    static_dir: str = os.getenv("STATIC_DIR", "static")

    # ── Database ──────────────────────────────────────────────────────────────
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/taskapp")
    mongo_db_name: str = os.getenv("MONGO_DB_NAME", "taskapp")

    # ── Auth ──────────────────────────────────────────────────────────────────
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    jwt_expires_in: str = os.getenv("JWT_EXPIRES_IN", "7d")

    # ── AI services ───────────────────────────────────────────────────────────
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    parakit_api_key: str = os.getenv("PARAKIT_API_KEY", "")
    parakit_api_endpoint: str = os.getenv(
        "PARAKIT_API_ENDPOINT", "https://api.parakit.io/v1/transcribe"
    )
    # Path to a PEM file (or directory) containing the CA certificate that
    # signed the Parakeet server's TLS certificate.  Leave empty to use the
    # default certifi bundle (correct for public endpoints).
    # Set to the path of your self-signed cert / private CA bundle when
    # Parakeet is running locally with a self-signed certificate.
    parakit_ca_bundle: str = os.getenv("PARAKIT_CA_BUNDLE", "")

    def validate(self) -> None:
        """Raise ValueError for any missing required secrets at startup."""
        missing = []
        if not self.jwt_secret:
            missing.append("JWT_SECRET")
        if not self.groq_api_key:
            missing.append("GROQ_API_KEY")
        if not self.parakit_api_key:
            missing.append("PARAKIT_API_KEY")
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()
    s.validate()
    return s


# Module-level singleton used throughout the app.
settings = get_settings()
