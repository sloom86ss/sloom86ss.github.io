#!/usr/bin/env python3
"""SLOOM365 SportScore connectivity check; never prints the API key."""
import json
import os
import urllib.error
import urllib.request

URL = "https://sportscore.com/api/widget/matches/?sport=football&limit=50&src=sloom86ss.github.io"

def main():
    key = os.getenv("SPORTSCORE_API_KEY", "").strip()
    if not key:
        raise SystemExit("SPORTSCORE_API_KEY is missing from GitHub Actions secrets")

    request = urllib.request.Request(
        URL,
        headers={
            "X-API-Key": key,
            "Accept": "application/json",
            "User-Agent": "SLOOM365/1.0 (+https://sloom86ss.github.io/)",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"SportScore HTTP {exc.code}; check API key and endpoint") from exc
    except Exception as exc:
        raise SystemExit(f"SportScore request failed: {type(exc).__name__}: {exc}") from exc

    matches = payload.get("matches") if isinstance(payload, dict) else None
    if not isinstance(matches, list):
        raise SystemExit("SportScore returned an unexpected JSON structure")
    print(json.dumps({
        "provider": "SportScore",
        "status": "connected",
        "matches_received": len(matches),
        "updated": payload.get("updated"),
        "sample_fields": sorted(matches[0].keys()) if matches else [],
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
