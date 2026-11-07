#!/usr/bin/env python3
"""SLOOM365 SportScore secondary collector.
Fetches public SportScore football matches and writes a SEPARATE snapshot.
It never edits data.json or overwrites ESPN/OpenLigaDB records.
"""
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "sportscore_backup.json"
URL = "https://sportscore.com/api/widget/matches/?sport=football&limit=50&src=sloom86ss.github.io"
HEADERS = {
    "User-Agent": "SLOOM365-SportScore-Backup/1.0 (+https://sloom86ss.github.io/)",
    "Accept": "application/json",
}

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def fetch():
    req = urllib.request.Request(URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError("SportScore HTTP " + str(response.status))
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("matches"), list):
        raise RuntimeError("SportScore returned an unexpected response: matches[] missing")
    return payload

def score(value):
    return None if value is None or value == "" else str(value)

def convert(item, index):
    if not isinstance(item, dict):
        return None
    home = str(item.get("home") or item.get("home_name") or "").strip()
    away = str(item.get("away") or item.get("away_name") or "").strip()
    if not home or not away:
        return None
    raw_status = str(item.get("status") or "").strip().lower()
    if raw_status in ("live", "in_play", "inplay", "in progress", "1h", "2h", "ht", "extra time", "penalties"):
        status = "in"
    elif raw_status in ("finished", "ft", "aet", "after penalties", "ended", "complete", "completed"):
        status = "post"
    elif raw_status in ("upcoming", "scheduled", "not started", "ns", "pre"):
        status = "pre"
    else:
        status = "unknown"
    slug = str(item.get("slug") or item.get("id") or "").strip()
    match_id = "sportscore:" + (slug or str(index))
    kickoff = item.get("time") or item.get("date") or ""
    return {
        "id": match_id,
        "slug": slug,
        "date": kickoff,
        "time": kickoff,
        "home": {
            "name": home,
            "logo": item.get("home_logo") or "",
            "score": score(item.get("home_score")),
        },
        "away": {
            "name": away,
            "logo": item.get("away_logo") or "",
            "score": score(item.get("away_score")),
        },
        "status": status,
        "detail": str(item.get("status_text") or item.get("status") or ""),
        "competition": str(item.get("competition") or item.get("league") or ""),
        "period": item.get("period"),
        "clock": str(item.get("clock") or ""),
        "data_source": "SportScore",
    }

def main():
    started = now()
    try:
        payload = fetch()
        matches = []
        skipped = 0
        for index, item in enumerate(payload["matches"]):
            row = convert(item, index)
            if row:
                matches.append(row)
            else:
                skipped += 1
        snapshot = {
            "provider": "SportScore",
            "source_url": URL,
            "checked_at": now(),
            "source_updated_at": payload.get("updated"),
            "sport": payload.get("sport", "football"),
            "count_reported": payload.get("count", len(payload["matches"])),
            "count_saved": len(matches),
            "skipped_invalid": skipped,
            "matches": matches,
            "status": "ok" if matches else "empty",
            "note": "Secondary snapshot only. Not merged into data.json; unknown live clocks are never invented.",
        }
        if not matches:
            raise RuntimeError("SportScore responded but no valid matches were found")
        temp = OUT.with_suffix(".json.tmp")
        temp.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(OUT)
        print(json.dumps({
            "status": snapshot["status"],
            "count_saved": len(matches),
            "source_updated_at": snapshot["source_updated_at"],
            "checked_at": snapshot["checked_at"],
            "skipped_invalid": skipped,
        }, ensure_ascii=False))
    except Exception as exc:
        failure = {
            "provider": "SportScore",
            "checked_at": now(),
            "status": "error",
            "error": str(exc)[:300],
            "matches": [],
        }
        # Preserve the last good snapshot if the provider is temporarily unavailable.
        if not OUT.exists():
            OUT.write_text(json.dumps(failure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("SportScore backup collector failed:", str(exc)[:300])
        raise

if __name__ == "__main__":
    main()
