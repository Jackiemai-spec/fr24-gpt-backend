import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any
import requests
from fastapi import HTTPException

FR24_BASE_URL = "https://fr24api.flightradar24.com/api"


def format_fr24_dt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def chunk_ranges(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    """Return <=14-day windows with 1-day overlap, matching FR24 Flight Summary limits."""
    windows: list[tuple[datetime, datetime]] = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=14), end)
        windows.append((cursor, chunk_end))
        cursor = cursor + timedelta(days=13)
    return windows


def fetch_flight_summary_full(registration: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
    token = os.environ.get("FR24_API_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="FR24_API_TOKEN is not configured")

    headers = {
        "Accept": "application/json",
        "Accept-Version": "v1",
        "Authorization": f"Bearer {token}",
    }

    all_items: list[dict[str, Any]] = []
    for from_dt, to_dt in chunk_ranges(start, end):
        params = {
            "flight_datetime_from": format_fr24_dt(from_dt),
            "flight_datetime_to": format_fr24_dt(to_dt),
            "registrations": registration.strip().upper(),
        }
        url = f"{FR24_BASE_URL}/flight-summary/full"
        resp = requests.get(url, headers=headers, params=params, timeout=60)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"FR24 API error {resp.status_code}: {resp.text[:500]}",
            )
        payload = resp.json()
        all_items.extend(payload.get("data") or [])
        time.sleep(0.25)

    return dedupe_raw_items(all_items)


def dedupe_raw_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for item in items:
        key = str(item.get("fr24_id") or "")
        if key:
            if key in seen:
                continue
            seen.add(key)
        output.append(item)
    return output
