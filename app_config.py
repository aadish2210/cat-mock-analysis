from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


class ConfigurationError(RuntimeError):
    pass


def _is_privileged_key(key: str) -> bool:
    if key.startswith("sb_secret_"):
        return True
    parts = key.split(".")
    if len(parts) != 3:
        return False
    try:
        padding = "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + padding))
    except (ValueError, TypeError, json.JSONDecodeError):
        return False
    return payload.get("role") == "service_role"


@dataclass(frozen=True)
class AppConfig:
    supabase_url: str | None = None
    supabase_key: str | None = None
    allowed_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )

    @property
    def cloud_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @property
    def storage_mode(self) -> str:
        return "supabase" if self.cloud_enabled else "local"

    @classmethod
    def from_env(cls) -> "AppConfig":
        url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
        key = (
            os.getenv("SUPABASE_PUBLISHABLE_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
            or ""
        ).strip()
        if bool(url) != bool(key):
            raise ConfigurationError(
                "Set both SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY "
                "(or SUPABASE_ANON_KEY), or leave both empty for local mode."
            )
        if os.getenv("VERCEL") and not url:
            raise ConfigurationError(
                "Vercel deployment requires SUPABASE_URL and "
                "SUPABASE_PUBLISHABLE_KEY."
            )
        if key and _is_privileged_key(key):
            raise ConfigurationError(
                "Never use a Supabase secret or service_role key here. "
                "Use the public publishable key (or legacy anon key)."
            )
        if url and not url.startswith("https://"):
            raise ConfigurationError("SUPABASE_URL must use https://")
        origins = tuple(
            origin.strip()
            for origin in os.getenv(
                "APP_ALLOWED_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        )
        return cls(url or None, key or None, origins)

    def public_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "mode": self.storage_mode,
            "auth_enabled": self.cloud_enabled,
        }
        if self.cloud_enabled:
            payload["supabase"] = {
                "url": self.supabase_url,
                "publishable_key": self.supabase_key,
            }
        return payload