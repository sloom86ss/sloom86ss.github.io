#!/usr/bin/env python3
"""Safely refresh currently-live football scores from GOAL API.

ESPN remains the site's primary source for fixtures, tables and teams.
This job only overlays GOAL API live scores onto fixtures already present
in data.json, so it cannot invent fixtures or replace competition metadata.
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data.json"
API_URL = "https://api.goal-api.com/v1/fixtures/live"
UTC = dt.timezone.utc


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm(value):
    value = clean(value).casefold()
    value = re.sub(r"[^\w]", "", value, flags=re.UNICODE)
    return value


def get_value(item, *keys):
    for key in keys:
        value = item.get(key)
        if value is not None and value != "":
            return value
    return None


def fetch_live(api_key):
    request = urllib.request.Request(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": "SLOOM365-live-scores/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise RuntimeError("GOAL API returned an unsuccessful response")
    matches = payload.get("data")
    if not isinstance(matches, list):
        raise RuntimeError("GOAL API response did not contain a data list")
    return matches


def main():
    api_key = os.environ.get("GOAL_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("GOAL_API_KEY secret is missing; no files were changed.")
    if not DATA_FILE.exists():
        raise SystemExit("data.json is missing; no files were changed.")

    try:
        live_matches = fetch_live(api_key)
    except urllib.error.HTTPError as exc:
        # Never print request headers or credentials.
        raise SystemExit(f"GOAL API request failed with HTTP {exc.code}; ESPN data was preserved.")
    except Exception as exc:
        raise SystemExit(f"GOAL API request failed ({type(exc).__name__}); ESPN data was preserved.")

    dataset = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    leagues = dataset.get("leagues") or {}
    index = {}
    for league_key, league in leagues.items():
        for match in league.get("matches") or []:
            home = norm((match.get("home") or {}).get("name"))
            away = norm((match.get("away") or {}).get("name"))
            if home and away:
                index[(home, away)] = match

    updated = 0
    unmatched = 0
    for item in live_matches:
        if not isinstance(item, dict):
            continue
        home_obj = item.get("homeTeam") if isinstance(item.get("homeTeam"), dict) else {}
        away_obj = item.get("awayTeam") if isinstance(item.get("awayTeam"), dict) else {}
        home_name = clean(get_value(item, "homeTeamName") or home_obj.get("name"))
        away_name = clean(get_value(item, "awayTeamName") or away_obj.get("name"))
        if not home_name or not away_name:
            continue

        match = index.get((norm(home_name), norm(away_name)))
        if match is None:
            # Some providers reverse home/away labels; match direction is still
            # preserved in the existing ESPN fixture, so try the reverse pair.
            match = index.get((norm(away_name), norm(home_name)))
            reversed_teams = match is not None
        else:
            reversed_teams = False
        if match is None:
            unmatched += 1
            continue

        home_score = get_value(item, "homeTeamScore", "homeScore")
        away_score = get_value(item, "awayTeamScore", "awayScore")
        if home_score is not None and away_score is not None:
            if reversed_teams:
                match["home"]["score"] = str(away_score)
                match["away"]["score"] = str(home_score)
            else:
                match["home"]["score"] = str(home_score)
                match["away"]["score"] = str(away_score)

        status = clean(get_value(item, "matchStatus", "status")).upper()
        if status in {"LIVE", "IN_PLAY", "INPLAY", "1H", "2H", "HT", "ET", "PEN"}:
            match["status"] = "in"
        elif status in {"FINISHED", "FT", "AET", "PEN_FINISHED"}:
            match["status"] = "post"
        elif status in {"SCHEDULED", "NOT_STARTED", "NS"}:
            match["status"] = "pre"

        minute = get_value(item, "matchMinute", "matchElapsed", "minute")
        period = clean(get_value(item, "matchPeriod") or "")
        match["clock"] = str(minute) if minute is not None else (period or match.get("clock"))
        match["status_short"] = status or match.get("status_short") or "LIVE"
        match["detail"] = str(minute) if minute is not None else (status or match.get("detail"))
        match["live_source"] = "GOAL API"
        updated += 1

    now = dt.datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    dataset["live_provider"] = "GOAL API (live scores) + ESPN (fixtures and fallback)"
    dataset["live_updated_at"] = now
    if updated:
        DATA_FILE.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"GOAL API checked {len(live_matches)} live fixtures; updated {updated} existing site fixtures; unmatched {unmatched}.")


if __name__ == "__main__":
    main()
