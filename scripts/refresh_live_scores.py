#!/usr/bin/env python3
"""Refresh SLOOM365 football fixtures and scores from ESPN only.

This lightweight job updates scoreboards without re-fetching team directories,
standings, or RSS news. Failed leagues retain their last verified payload.
"""
import concurrent.futures
import datetime as dt
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data.json"
UTC = dt.timezone.utc
NOW = dt.datetime.now(UTC)
NOW_ISO = NOW.isoformat(timespec="seconds").replace("+00:00", "Z")
DATE_RANGE = (
    f"{(NOW.date() - dt.timedelta(days=1)):%Y%m%d}-"
    f"{(NOW.date() + dt.timedelta(days=2)):%Y%m%d}"
)
BASE = "https://site.api.espn.com/apis/site/v2/sports/"
HEADERS = {"User-Agent": "SLOOM365-Live-Scores/1.0 (+https://sloom86ss.github.io/)"}


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def iso(value):
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    except (TypeError, ValueError):
        return None


def fetch_scoreboard(key):
    url = BASE + urllib.parse.quote(key, safe="/.") + "/scoreboard?" + urllib.parse.urlencode({
        "dates": DATE_RANGE, "limit": 500
    })
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        raise RuntimeError("ESPN returned an invalid scoreboard")
    return payload["events"]


def parse_event(event, league_name):
    competitions = event.get("competitions") or []
    if not competitions:
        return None
    comp = competitions[0]
    competitors = comp.get("competitors") or []
    home = next((x for x in competitors if x.get("homeAway") == "home"), None)
    away = next((x for x in competitors if x.get("homeAway") == "away"), None)
    if not home or not away:
        return None

    status = ((comp.get("status") or {}).get("type") or
              (event.get("status") or {}).get("type") or {})
    state = status.get("state")
    if state not in ("pre", "in", "post"):
        state_name = clean(status.get("name")).lower()
        state = "post" if any(x in state_name for x in ("final", "full")) else "pre"

    def club(item):
        team = item.get("team") or {}
        logos = team.get("logos") or []
        return {
            "id": str(team.get("id") or ""),
            "name": clean(team.get("displayName") or team.get("name")),
            "short_name": clean(team.get("shortDisplayName") or team.get("abbreviation") or team.get("name")),
            "logo": (logos[0].get("href") or "") if logos else (team.get("logo") or ""),
            "score": str(item.get("score")) if item.get("score") is not None else None,
            "abbreviation": clean(team.get("abbreviation")),
        }

    broadcasts = []
    for item in comp.get("broadcasts") or []:
        broadcasts.extend(clean(x) for x in (item.get("names") or []) if clean(x))

    date = iso(event.get("date"))
    return {
        "id": str(event.get("id") or ""),
        "date": date,
        "time": date,
        "home": club(home),
        "away": club(away),
        "status": state,
        "detail": clean(status.get("shortDetail") or status.get("detail") or status.get("description")),
        "status_detail": clean(status.get("detail") or status.get("description")),
        "status_short": clean(status.get("shortDetail") or status.get("name")),
        "period": (comp.get("status") or {}).get("period"),
        "clock": (comp.get("status") or {}).get("displayClock"),
        "venue": clean((comp.get("venue") or {}).get("fullName")),
        "broadcast": "، ".join(dict.fromkeys(broadcasts)) or None,
        "league": league_name,
    }


def refresh_one(item):
    key, previous = item
    events = fetch_scoreboard(key)
    name = previous.get("name") or key
    matches = [match for match in (parse_event(event, name) for event in events) if match]
    updated = dict(previous)
    updated["name"] = name
    updated["category"] = previous.get("category") or "football"
    updated["matches"] = sorted(matches, key=lambda match: match.get("date") or "")
    updated["updated_at"] = NOW_ISO
    updated["live_checked_at"] = NOW_ISO
    updated["live_refresh_error"] = ""
    updated["stale"] = False
    return key, updated, len(matches)


def main():
    if not DATA_FILE.exists():
        raise SystemExit("data.json is missing; no files were changed.")
    dataset = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    leagues = dataset.get("leagues")
    if not isinstance(leagues, dict) or not leagues:
        raise SystemExit("No league records found; no files were changed.")

    refreshed = {}
    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(refresh_one, (key, value)): key
                   for key, value in leagues.items() if isinstance(value, dict)}
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            try:
                refreshed_key, value, count = future.result()
                refreshed[refreshed_key] = value
                print(f"{key}: refreshed {count} fixtures")
            except Exception as exc:
                errors.append(f"{key}: {type(exc).__name__}: {str(exc)[:120]}")
                print(f"{key}: refresh failed; previous verified data preserved")

    if not refreshed:
        raise SystemExit("All ESPN scoreboard requests failed; data.json was not changed.")

    final_leagues = {}
    for key, value in leagues.items():
        if key in refreshed:
            final_leagues[key] = refreshed[key]
        else:
            preserved = dict(value)
            preserved["stale"] = True
            preserved["live_refresh_error"] = next((entry for entry in errors if entry.startswith(key + ":")), "ESPN refresh failed")
            final_leagues[key] = preserved
    dataset["leagues"] = final_leagues
    dataset["generated_at"] = NOW_ISO
    dataset["live_updated_at"] = NOW_ISO
    dataset["live_provider"] = "ESPN public scoreboard API"
    dataset["live_refresh_errors"] = errors[:30]
    DATA_FILE.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {len(refreshed)}/{len(leagues)} leagues; {len(errors)} failures.")


if __name__ == "__main__":
    main()
