#!/usr/bin/env python3
"""SLOOM TV data collector. ESPN public endpoints; failed feeds never erase good data."""
import json, os, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

BASE = "https://site.api.espn.com/apis/site/v2/sports"
STANDINGS_BASE = "https://site.api.espn.com/apis/v2/sports"
FEEDS = {
    "soccer/eng.1": ("الدوري الإنجليزي الممتاز", "football"),
    "soccer/esp.1": ("الدوري الإسباني", "football"),
    "soccer/ita.1": ("الدوري الإيطالي", "football"),
    "soccer/ger.1": ("الدوري الألماني", "football"),
    "soccer/fra.1": ("الدوري الفرنسي", "football"),
    "soccer/ksa.1": ("دوري روشن السعودي", "football"),
    "soccer/por.1": ("الدوري البرتغالي", "football"),
    "soccer/ned.1": ("الدوري الهولندي", "football"),
    "soccer/bra.1": ("الدوري البرازيلي", "football"),
    "soccer/arg.1": ("الدوري الأرجنتيني", "football"),
    "soccer/uefa.champions": ("دوري أبطال أوروبا", "football"),
    "soccer/uefa.europa": ("الدوري الأوروبي", "football"),
    "soccer/fifa.world": ("كأس العالم", "football"),
    "basketball/nba": ("دوري NBA لكرة السلة", "basketball"),
    "basketball/wnba": ("دوري WNBA", "basketball"),
    "football/nfl": ("دوري NFL", "americanfootball"),
    "hockey/nhl": ("دوري NHL للهوكي", "hockey"),
    "baseball/mlb": ("دوري MLB للبيسبول", "baseball"),
    "mma/ufc": ("UFC والفنون القتالية", "other"),
}
NOW = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def get_json(url, attempts=3):
    last = None
    for n in range(attempts):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; SLOOM-TV/2.0; sports data)",
                "Accept": "application/json"
            })
            with urllib.request.urlopen(req, timeout=15) as response:
                if response.status != 200:
                    raise RuntimeError("HTTP " + str(response.status))
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last = exc
            if n + 1 < attempts:
                time.sleep(0.8 * (n + 1))
    raise last

def team_rows(payload):
    rows = []
    for sport in payload.get("sports", []):
        for league in sport.get("leagues", []):
            for item in league.get("teams", []):
                team = item.get("team", item)
                if team.get("displayName"):
                    rows.append({
                        "id": str(team.get("id", "")),
                        "name": team.get("displayName", ""),
                        "short_name": team.get("shortDisplayName", ""),
                        "logo": team.get("logo") or ((team.get("logos") or [{}])[0].get("href", "")),
                        "abbreviation": team.get("abbreviation", "")
                    })
    return rows

def standings_rows(payload):
    rows = []
    for child in payload.get("children", []):
        rows.extend(standings_rows(child))
    for group in payload.get("standings", {}).get("entries", []):
        stats = {x.get("name"): x.get("displayValue") for x in group.get("stats", [])}
        team = group.get("team", {})
        rows.append({
            "name": team.get("displayName", team.get("name", "")),
            "logo": team.get("logos", [{}])[0].get("href", "") if team.get("logos") else "",
            "rank": stats.get("rank", ""),
            "points": stats.get("points", ""),
            "played": stats.get("gamesPlayed", ""),
            "wins": stats.get("wins", ""),
            "draws": stats.get("ties", ""),
            "losses": stats.get("losses", ""),
            "goal_difference": stats.get("pointDifferential", "")
        })
    return rows

def fetch_feed(item):
    key, (name, category) = item
    result = {"name": name, "category": category, "matches": [], "news": [],
              "teams": [], "standings": [], "updated_at": None, "stale": False}
    errors = []
    try:
        payload = get_json(f"{BASE}/{key}/scoreboard")
        for event in payload.get("events", []):
            comp = (event.get("competitions") or [{}])[0]
            competitors = comp.get("competitors", [])
            home = next((x for x in competitors if x.get("homeAway") == "home"), {})
            away = next((x for x in competitors if x.get("homeAway") == "away"), {})
            status = (comp.get("status") or {}).get("type", {})
            ht, at = home.get("team") or {}, away.get("team") or {}
            result["matches"].append({
                "id": str(event.get("id", "")),
                "date": event.get("date", ""),
                "time": event.get("date", ""),
                "home": {"name": ht.get("displayName", ht.get("shortDisplayName", "الفريق الأول")),
                         "logo": ht.get("logo", ""), "score": home.get("score")},
                "away": {"name": at.get("displayName", at.get("shortDisplayName", "الفريق الثاني")),
                         "logo": at.get("logo", ""), "score": away.get("score")},
                "status": status.get("state", "pre"),
                "detail": status.get("shortDetail") or status.get("detail", ""),
                "venue": (comp.get("venue") or {}).get("fullName", ""),
                "broadcast": ", ".join(x.get("names", [""])[0] for x in comp.get("broadcasts", []) if x.get("names"))
            })
        result["updated_at"] = NOW()
    except Exception as exc:
        errors.append("scoreboard: " + str(exc)[:140])
    try:
        payload = get_json(f"{BASE}/{key}/news")
        for article in payload.get("articles", [])[:10]:
            images = article.get("images") or []
            result["news"].append({
                "headline": article.get("headline") or article.get("description") or "خبر رياضي",
                "description": article.get("description", ""),
                "link": (article.get("links", {}).get("web") or {}).get("href", ""),
                "image": images[0].get("url", "") if images else "",
                "source": name,
                "published": article.get("published", "")
            })
    except Exception as exc:
        errors.append("news: " + str(exc)[:100])
    if category == "football":
        try:
            result["teams"] = team_rows(get_json(f"{BASE}/{key}/teams"))
        except Exception as exc:
            errors.append("teams: " + str(exc)[:100])
        try:
            result["standings"] = standings_rows(get_json(f"{STANDINGS_BASE}/{key}/standings"))
        except Exception as exc:
            errors.append("standings: " + str(exc)[:100])
    result["errors"] = errors
    return key, result

def main():
    path = os.path.join(os.path.dirname(__file__), "data.json")
    try:
        with open(path, encoding="utf-8") as f:
            previous = json.load(f)
    except Exception:
        previous = {}
    old_leagues = previous.get("leagues", previous if isinstance(previous, dict) else {})
    output = {"generated_at": NOW(), "timezone": "Asia/Muscat", "provider": "ESPN public API", "leagues": {}}
    success = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(fetch_feed, item) for item in FEEDS.items()]
        for future in as_completed(futures):
            try:
                key, data = future.result()
                if data["updated_at"]:
                    success += 1
                else:
                    old = old_leagues.get(key, {})
                    # Retain old content for reference, but clearly mark it stale.
                    for field in ("matches", "news", "teams", "standings"):
                        if not data[field] and old.get(field):
                            data[field] = old[field]
                    data["updated_at"] = old.get("updated_at")
                    data["stale"] = True
                output["leagues"][key] = data
                print(f"{key}: matches={len(data['matches'])}, teams={len(data['teams'])}, stale={data['stale']}, errors={len(data['errors'])}")
            except Exception as exc:
                print("Feed task failed:", str(exc)[:200])
    if success == 0:
        raise SystemExit("No scoreboard feed succeeded; keeping existing data.json unchanged.")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Published {success}/{len(FEEDS)} current scoreboards; total matches={sum(len(x['matches']) for x in output['leagues'].values())}")

if __name__ == "__main__":
    main()
