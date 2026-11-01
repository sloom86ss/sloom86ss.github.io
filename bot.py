#!/usr/bin/env python3
"""Fetch public ESPN scoreboard and news feeds and write data.json."""
import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

BASE = "https://site.api.espn.com/apis/site/v2/sports"
FEEDS = {
    "soccer/eng.1": ("الدوري الإنجليزي", "football"),
    "soccer/esp.1": ("الدوري الإسباني", "football"),
    "soccer/ger.1": ("الدوري الألماني", "football"),
    "soccer/ita.1": ("الدوري الإيطالي", "football"),
    "soccer/fra.1": ("الدوري الفرنسي", "football"),
    "soccer/uefa.champions": ("دوري أبطال أوروبا", "football"),
    "soccer/uefa.europa": ("الدوري الأوروبي", "football"),
    "basketball/nba": ("دوري NBA لكرة السلة", "basketball"),
    "basketball/wnba": ("دوري WNBA", "basketball"),
    "football/nfl": ("دوري NFL", "americanfootball"),
    "hockey/nhl": ("دوري NHL للهوكي", "hockey"),
    "baseball/mlb": ("دوري MLB للبيسبول", "baseball"),
    "mma/ufc": ("UFC والفنون القتالية", "other"),
}

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SLOOM-TV/1.0 (sports scoreboard)"})
    with urllib.request.urlopen(req, timeout=18) as response:
        return json.loads(response.read().decode("utf-8"))

def fetch_feed(item):
    key, (name, category) = item
    result = {"name": name, "category": category, "matches": [], "news": [],
              "updated_at": datetime.now(timezone.utc).isoformat()}
    try:
        payload = get_json(f"{BASE}/{key}/scoreboard")
        for event in payload.get("events", []):
            comp = (event.get("competitions") or [{}])[0]
            competitors = comp.get("competitors", [])
            home = next((x for x in competitors if x.get("homeAway") == "home"), {})
            away = next((x for x in competitors if x.get("homeAway") == "away"), {})
            status = (comp.get("status") or {}).get("type", {})
            result["matches"].append({
                "id": event.get("id"),
                "home": {"name": (home.get("team") or {}).get("displayName", "الفريق الأول"),
                         "logo": (home.get("team") or {}).get("logo", ""),
                         "score": home.get("score")},
                "away": {"name": (away.get("team") or {}).get("displayName", "الفريق الثاني"),
                         "logo": (away.get("team") or {}).get("logo", ""),
                         "score": away.get("score")},
                "status": status.get("state", "pre"),
                "detail": status.get("shortDetail") or status.get("detail", ""),
                "time": event.get("date", ""),
            })
    except Exception as exc:
        result["scoreboard_error"] = str(exc)[:180]
    try:
        payload = get_json(f"{BASE}/{key}/news")
        for article in payload.get("articles", [])[:8]:
            images = article.get("images") or []
            result["news"].append({
                "headline": article.get("headline") or article.get("description") or "خبر رياضي",
                "link": article.get("links", {}).get("web", {}).get("href", ""),
                "image": (images[0].get("url", "") if images else ""),
                "source": name,
            })
    except Exception:
        pass
    return key, result

def main():
    output = {"generated_at": datetime.now(timezone.utc).isoformat(), "leagues": {}}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(fetch_feed, item) for item in FEEDS.items()]
        for future in as_completed(futures):
            try:
                key, data = future.result()
                output["leagues"][key] = data
            except Exception as exc:
                print(f"Feed failed: {exc}")
    path = os.path.join(os.path.dirname(__file__), "data.json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)
    match_count = sum(len(x.get("matches", [])) for x in output["leagues"].values())
    print(f"Updated {len(output['leagues'])} feeds and {match_count} matches.")

if __name__ == "__main__":
    main()
