from __future__ import annotations

import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

from app_config import AppConfig, ROOT


MIGRATION = ROOT / "supabase" / "migrations" / "20260904000000_initial.sql"


def project_ref(url: str) -> str:
    match = re.fullmatch(r"https://([a-z0-9-]+)\.supabase\.co", url.rstrip("/"))
    if not match:
        raise ValueError("SUPABASE_URL must look like https://PROJECT_REF.supabase.co")
    return match.group(1)


def main() -> None:
    load_dotenv(ROOT / ".env")
    config = AppConfig.from_env()
    if not config.cloud_enabled:
        raise SystemExit("Add SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY to .env first.")
    sql = MIGRATION.read_text(encoding="utf-8")
    access_token = (os.getenv("SUPABASE_ACCESS_TOKEN") or "").strip()
    if not access_token:
        print("Runtime configuration is valid.")
        print("One database provisioning step remains:")
        print(f"1. Open the Supabase SQL Editor for project {project_ref(config.supabase_url or '')}.")
        print(f"2. Run the contents of: {MIGRATION}")
        print("3. Start the app and create the first account.")
        return

    response = requests.post(
        f"https://api.supabase.com/v1/projects/{project_ref(config.supabase_url or '')}/database/query",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"query": sql},
        timeout=90,
    )
    if not response.ok:
        raise SystemExit(f"Schema setup failed ({response.status_code}): {response.text[:400]}")
    print("Supabase schema, profiles, and row-level security policies are ready.")


if __name__ == "__main__":
    main()