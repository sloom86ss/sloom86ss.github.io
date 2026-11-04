#!/usr/bin/env python3
"""Overlay Sportmonks live scores onto already-known SLOOM365 fixtures.
ESPN remains the source of fixture lists and competition metadata.
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
API_URL = "https://api.sportmonks.com/v3/football/livescores"
UTC = dt.timezone.utc


def clean(value):
    return re.sub(r"\\s+", " ", str(value or "")).strip()


def norm(value):
    value = clean(value).casefold()
    return re.sub(r"[^\\w]", "", value, flags=re.UNICODE)


def fetch_live(token):
    request = urllib.request.Request(
        API_URL + "?include=participants;scores;state;periods",
        headers={
            "Authorization": token,
            "Accept": "application/json",
            "User-Agent": "SLOOM365-Sportmonks/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError("Sportmonks returned an unexpected response structure")
    return payload["data"]


def fixture_teams(item):
    participants = item.get("participants") or []
    home = away = None
    for participant in participants:
        location = ((participant.get("meta") or {}).get("location") or "").lower()
        if location == "home":
            home = participant
        elif location == "away":
            away = participant
    if home and away:
        return clean(home.get("name")), clean(away.get("name"))
    name = clean(item.get("name"))
    if " vs " in name:
        left, right = name.split(" vs ", 1)
        return clean(left), clean(right)
    return "", ""


def current_scores(item):
    result = {}
    for entry in item.get("scores") or []:
        if clean(entry.get("description")).upper() != "CURRENT":
            continue
        score = entry.get("score") or {}
        side = clean(score.get("participant")).lower()
        goals = score.get("goals")
        if side in ("home", "away") and goals is not None:
            result[side] = goals
    return result


def state_values(item):
    state = item.get("state") or {}
    return " ".join(clean(state.get(k)) for k in ("state", "name", "short_name", "developer_name")).upper()


def main():
    token = os.environ.get("SPORTMONKS_TOKEN", "").strip()
    if not token:
        raise SystemExit("SPORTMONKS_TOKEN secret is missing; no files were changed.")
    if not DATA_FILE.exists():
        raise SystemExit("data.json is missing; no files were changed.")

    try:
        live_fixtures = fetch_live(token)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Sportmonks request failed with HTTP {exc.code}; existing site data was preserved.")
    except Exception as exc:
        raise SystemExit(f"Sportmonks request failed ({type(exc).__name__}); existing site data was preserved.")

    dataset = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    leagues = dataset.get("leagues") or {}
    index = {}
    for league in leagues.values():
        for match in league.get("matches") or []:
            home = norm((match.get("home") or {}).get("name"))
            away = norm((match.get("away") or {}).get("name"))
            if home and away:
                index[(home, away)] = match

    updated = unmatched = without_score = 0
    for item in live_fixtures:
        if not isinstance(item, dict):
            continue
        home_name, away_name = fixture_teams(item)
        if not home_name or not away_name:
            continue
        match = index.get((norm(home_name), norm(away_name)))
        reversed_teams = False
        if match is None:
            match = index.get((norm(away_name), norm(home_name)))
            reversed_teams = match is not None
        if match is None:
            unmatched += 1
            continue

        scores = current_scores(item)
        if "home" not in scores or "away" not in scores:
            without_score += 1
            continue
        if reversed_teams:
            match["home"]["score"] = str(scores["away"])
            match["away"]["score"] = str(scores["home"])
        else:
            match["home"]["score"] = str(scores["home"])
            match["away"]["score"] = str(scores["away"])

        state_text = state_values(item)
        state_obj = item.get("state") or {}
        state_code = clean(state_obj.get("state")).upper()
        if any(x in state_text for x in ("LIVE", "INPLAY", "IN PLAY", "1ST HALF", "2ND HALF", "HALF TIME", "EXTRA TIME", "PENALT")):
            match["status"] = "in"
        elif any(x in state_text for x in ("FINISHED", "FT", "AFTER EXTRA TIME", "AFTER PENALTIES")):
            match["status"] = "post"
        elif any(x in state_text for x in ("NOT STARTED", "SCHEDULED")):
            match["status"] = "pre"

        periods = item.get("periods") or []
        minute = next((p.get("minutes") for p in reversed(periods) if p.get("ticking") and p.get("minutes") is not None), None)
        if minute is not None:
            match["clock"] = str(minute)
            match["detail"] = str(minute)
        elif state_obj.get("name"):
            match["detail"] = clean(state_obj.get("name"))
        match["status_short"] = clean(state_obj.get("short_name") or state_obj.get("name") or state_code or "LIVE")
        match["live_source"] = "Sportmonks"
        updated += 1

    now = dt.datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    dataset["live_provider"] = "Sportmonks (live scores) + ESPN (fixtures and fallback)"
    dataset["live_updated_at"] = now
    if updated:
        DATA_FILE.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    print(f"Sportmonks returned {len(live_fixtures)} livescore fixtures; updated {updated} existing site fixtures; unmatched {unmatched}; without current score {without_score}.")
    if live_fixtures and updated == 0:
        print("No existing site fixture matched. ESPN data was preserved; team-name mapping may be needed.")


if __name__ == "__main__":
    main()
