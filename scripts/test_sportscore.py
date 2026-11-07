#!/usr/bin/env python3
"""Safe connectivity/schema probe for the SportScore backup feed.

This first-stage probe never edits data.json and never prints the API key.
It requests a small UTC date window and reports only response structure.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://sportscore.com/api/v1/fixtures/"
KEY = os.getenv("SPORTSCORE_API_KEY", "").strip()
HEADERS = {
    "User-Agent": "SLOOM365-SportScore-Probe/1.0 (+https://sloom86ss.github.io/)",
    "Accept": "application/json",
}
if KEY:
    HEADERS["X-Api-Key"] = KEY

def fetch(day):
    params = urllib.parse.urlencode({"sport": "football", "date": day, "limit": 200})
    req = urllib.request.Request(BASE + "?" + params, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as response:
        body = response.read()
        if response.status != 200:
            raise RuntimeError("HTTP " + str(response.status))
    payload = json.loads(body.decode("utf-8"))
    if isinstance(payload, list):
        rows = payload
        top_keys = ["<list>"]
    elif isinstance(payload, dict):
        top_keys = sorted(payload.keys())
        rows = None
        for name in ("fixtures", "matches", "data", "results"):
            if isinstance(payload.get(name), list):
                rows = payload[name]
                break
        if rows is None:
            rows = []
    else:
        raise RuntimeError("Unexpected JSON root type: " + type(payload).__name__)
    sample = rows[0] if rows and isinstance(rows[0], dict) else {}
    return {
        "date": day,
        "count": len(rows),
        "root_keys": top_keys[:30],
        "match_keys": sorted(sample.keys())[:50],
        "sample": {
            k: sample.get(k) for k in (
                "id", "slug", "home", "away", "home_team", "away_team",
                "home_score", "away_score", "status", "status_text",
                "time", "date", "competition"
            ) if k in sample
        },
    }

def main():
    if not KEY:
        print("SPORTSCORE_API_KEY is not configured; probe skipped.")
        return 0
    today = datetime.now(timezone.utc).date()
    reports = []
    errors = []
    for offset in (-1, 0, 1):
        day = (today + timedelta(days=offset)).isoformat()
        try:
            reports.append(fetch(day))
        except Exception as exc:
            errors.append({"date": day, "error": str(exc)[:220]})
    print("SportScore connectivity/schema probe:")
    print(json.dumps({"reports": reports, "errors": errors}, ensure_ascii=False))
    # Keep this probe non-blocking for the primary football collector.
    return 0

if __name__ == "__main__":
    sys.exit(main())
