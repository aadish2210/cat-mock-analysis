from __future__ import annotations

import sys

import requests

from app_config import AppConfig, ConfigurationError


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def main() -> None:
    try:
        config = AppConfig.from_env()
    except ConfigurationError as error:
        fail(str(error))
    if not config.cloud_enabled:
        fail("Supabase is not configured. Copy .env.example to .env and add both public values.")

    headers = {
        "apikey": config.supabase_key or "",
        "Authorization": f"Bearer {config.supabase_key}",
        "Accept": "application/json",
    }
    print("[PASS] Environment contains a valid HTTPS project URL and public key shape.")

    try:
        auth_response = requests.get(
            f"{config.supabase_url}/auth/v1/settings",
            headers=headers,
            timeout=20,
        )
    except requests.RequestException as error:
        fail(f"Could not reach Supabase Auth: {error}")
    if not auth_response.ok:
        fail(
            f"Supabase Auth rejected the project URL/key "
            f"({auth_response.status_code})."
        )
    print("[PASS] Supabase Auth is reachable and accepts the publishable key.")

    try:
        schema_response = requests.post(
            f"{config.supabase_url}/rest/v1/rpc/cat_portal_health",
            headers={**headers, "Content-Type": "application/json"},
            json={},
            timeout=20,
        )
    except requests.RequestException as error:
        fail(f"Could not reach the Supabase Data API: {error}")
    if not schema_response.ok:
        fail(
            "The portal schema is not ready. Run "
            "supabase/migrations/20260904000000_initial.sql in the SQL Editor. "
            f"Supabase returned {schema_response.status_code}."
        )
    payload = schema_response.json()
    if payload.get("schema_version") != "20260904000000":
        fail("The database responded, but its portal schema version is unexpected.")
    print("[PASS] Tables, RLS migration, and Data API health function are installed.")
    print("\nSupabase preflight complete. Start the app and create the first account.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)