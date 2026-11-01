#!/usr/bin/env python3
"""Refresh SLOOM360 football data from public ESPN endpoints and trusted RSS feeds.

The updater never fabricates a result. A failed league request preserves its previous
payload and marks that league stale so the website can hide it.
"""
import datetime as dt
import email.utils
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data.json"
UTC = dt.timezone.utc
NOW = dt.datetime.now(UTC)
NOW_ISO = NOW.isoformat(timespec="seconds").replace("+00:00", "Z")
DATE_RANGE = f"{(NOW.date()-dt.timedelta(days=1)):%Y%m%d}-{(NOW.date()+dt.timedelta(days=2)):%Y%m%d}"
BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
LEAGUES = {
    "soccer/eng.1": "eng.1", "soccer/esp.1": "esp.1", "soccer/ita.1": "ita.1",
    "soccer/ger.1": "ger.1", "soccer/fra.1": "fra.1", "soccer/ksa.1": "ksa.1",
    "soccer/por.1": "por.1", "soccer/ned.1": "ned.1", "soccer/uefa.champions": "uefa.champions",
    "soccer/uefa.europa": "uefa.europa", "soccer/arg.1": "arg.1", "soccer/bra.1": "bra.1",
    "soccer/fifa.world": "fifa.world",
}
TRUSTED_RSS = [
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    ("The Guardian", "https://www.theguardian.com/football/rss"),
    ("Sky Sports", "https://www.skysports.com/rss/12040"),
]
HEADERS = {"User-Agent": "SLOOM360-Football-Data/1.0 (+https://sloom86ss.github.io/)"}

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=18) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))

def fetch_text(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=18) as response:
        return response.read()

def iso(value):
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    except Exception:
        try:
            parsed = email.utils.parsedate_to_datetime(str(value))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        except Exception:
            return None

def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def logo_for(team):
    logos = team.get("logos") or []
    if logos:
        return logos[0].get("href") or ""
    return ""

def event_match(event, league_name):
    competitions = event.get("competitions") or []
    if not competitions:
        return None
    comp = competitions[0]
    competitors = comp.get("competitors") or []
    home = next((x for x in competitors if x.get("homeAway") == "home"), None)
    away = next((x for x in competitors if x.get("homeAway") == "away"), None)
    if not home or not away:
        return None
    status = (event.get("status") or {}).get("type") or {}
    state = status.get("state")
    status_name = (status.get("name") or "").lower()
    if state not in ("pre", "in", "post"):
        state = "pre" if "sched" in status_name else "post" if "final" in status_name else "pre"
    def club(c):
        t = c.get("team") or {}
        score = c.get("score")
        return {
            "id": str(t.get("id") or ""),
            "name": clean(t.get("displayName") or t.get("name")),
            "short_name": clean(t.get("shortDisplayName") or t.get("abbreviation") or t.get("name")),
            "logo": logo_for(t),
            "score": str(score) if score is not None else None,
            "abbreviation": clean(t.get("abbreviation")),
        }
    broadcasts = []
    for item in comp.get("broadcasts") or []:
        names = item.get("names") or []
        broadcasts.extend(clean(x) for x in names if clean(x))
    detail = clean(status.get("shortDetail") or status.get("detail") or status.get("description"))
    return {
        "id": str(event.get("id") or ""),
        "date": iso(event.get("date")),
        "time": iso(event.get("date")),
        "home": club(home),
        "away": club(away),
        "status": state,
        "detail": detail,
        "status_detail": clean(status.get("detail") or status.get("description")),
        "status_short": clean(status.get("shortDetail") or status.get("name")),
        "period": (event.get("status") or {}).get("period"),
        "clock": (event.get("status") or {}).get("displayClock"),
        "venue": clean((comp.get("venue") or {}).get("fullName")),
        "broadcast": "، ".join(dict.fromkeys(broadcasts)) or None,
        "league": league_name,
    }

def parse_teams(payload):
    result = []
    sports = payload.get("sports") or []
    for sport in sports:
        for league in sport.get("leagues") or []:
            for item in league.get("teams") or []:
                t = item.get("team") or item
                name = clean(t.get("displayName") or t.get("name"))
                if name:
                    result.append({"id": str(t.get("id") or ""), "name": name,
                                   "short_name": clean(t.get("shortDisplayName") or t.get("abbreviation") or name),
                                   "logo": logo_for(t), "abbreviation": clean(t.get("abbreviation"))})
    return result

def parse_standings(payload):
    entries = []
    def walk(node):
        if isinstance(node, dict):
            for item in node.get("entries") or []:
                team = item.get("team") or {}
                stats = {x.get("name"): x.get("displayValue", x.get("value")) for x in item.get("stats") or []}
                name = clean(team.get("displayName") or team.get("name"))
                if name:
                    entries.append({
                        "name": name, "logo": logo_for(team),
                        "rank": str(stats.get("rank") or stats.get("playoffSeed") or len(entries)+1),
                        "played": str(stats.get("gamesPlayed") or stats.get("played") or "—"),
                        "points": str(stats.get("points") or "—"),
                        "wins": str(stats.get("wins") or "—"),
                        "draws": str(stats.get("ties") or stats.get("draws") or "—"),
                        "losses": str(stats.get("losses") or "—"),
                        "goal_difference": str(stats.get("pointDifferential") or "—"),
                    })
            for value in node.values():
                if isinstance(value, (dict, list)):
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(payload)
    unique = {}
    for row in entries:
        unique[row["name"]] = row
    return sorted(unique.values(), key=lambda x: int(x["rank"]) if x["rank"].isdigit() else 999)

def parse_rss(source, url):
    raw = fetch_text(url)
    root = ET.fromstring(raw)
    items = []
    for item in root.findall(".//item")[:25]:
        headline = clean(item.findtext("title"))
        link = clean(item.findtext("link"))
        published = iso(item.findtext("pubDate"))
        description = clean(re.sub(r"<[^>]+>", " ", item.findtext("description") or ""))
        if not headline or not link.startswith("https://") or not published:
            continue
        category_text = (headline + " " + description).lower()
        category = "transfers" if any(k in category_text for k in ("transfer", "signing", "deal agreed", "loan move", "joins", "signs for", "انتقال", "صفقة", "تعاقد")) else "news"
        publisher_node = item.find("source")
        publisher = clean(publisher_node.text) if source == "Google News" and publisher_node is not None else ""
        display_source = (publisher + " عبر Google News") if publisher else source
        items.append({"headline": headline, "description": description[:900], "link": link,
                      "published": published, "fetched_at": NOW_ISO, "source": display_source,
                      "discovery_source": source, "category": category})
    return items

def main():
    if not DATA_FILE.exists():
        raise SystemExit("data.json is missing; refusing to create an incomplete dataset.")
    old = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    leagues = old.get("leagues") or {}
    updated = dict(old)
    successful = 0
    errors = []
    for key, slug in LEAGUES.items():
        previous = dict(leagues.get(key) or {})
        league_name = previous.get("name") or key
        base_url = f"{BASE}/{urllib.parse.quote(slug, safe='.')}"
        try:
            scoreboard = fetch_json(base_url + "/scoreboard?" + urllib.parse.urlencode({"dates": DATE_RANGE, "limit": 100}))
            events = scoreboard.get("events") or []
            matches = [m for m in (event_match(e, league_name) for e in events) if m]
            previous["matches"] = sorted(matches, key=lambda x: x.get("date") or "")
            # Keep the site's Arabic competition label; ESPN's provider label is often English.
            previous["name"] = league_name
            previous["category"] = "football"
            previous["updated_at"] = NOW_ISO
            previous["stale"] = False
            successful += 1
            try:
                teams = parse_teams(fetch_json(base_url + "/teams?limit=100"))
                if teams:
                    previous["teams"] = teams
            except Exception as exc:
                errors.append(f"{key} teams: {exc}")
            try:
                table = parse_standings(fetch_json(base_url + "/standings"))
                if table:
                    previous["standings"] = table
            except Exception as exc:
                errors.append(f"{key} standings: {exc}")
            leagues[key] = previous
        except Exception as exc:
            previous["stale"] = True
            leagues[key] = previous
            errors.append(f"{key} scoreboard: {exc}")
        time.sleep(0.15)

    news = []
    for source, url in TRUSTED_RSS:
        try:
            news.extend(parse_rss(source, url))
        except Exception as exc:
            errors.append(f"{source} RSS: {exc}")
    try:
        espn = fetch_json(BASE + "/eng.1/news?limit=25")
        for item in espn.get("articles") or []:
            headline = clean(item.get("headline") or item.get("title"))
            link = clean(item.get("links", {}).get("web", {}).get("href"))
            published = iso(item.get("published") or item.get("lastModified"))
            if headline and link.startswith("https://") and published:
                news.append({"headline": headline, "description": clean(item.get("description"))[:900],
                             "link": link, "published": published, "fetched_at": NOW_ISO,
                             "source": "ESPN", "category": "transfers" if "transfer" in headline.lower() else "news"})
    except Exception as exc:
        errors.append(f"ESPN news: {exc}")

    dedup = {}
    cutoff = NOW - dt.timedelta(days=7)
    for item in news:
        published = iso(item.get("published"))
        if not published:
            continue
        when = dt.datetime.fromisoformat(published.replace("Z", "+00:00"))
        if when > NOW + dt.timedelta(hours=1) or when < cutoff:
            continue
        dedup[item["link"]] = item
    fresh_news = sorted(dedup.values(), key=lambda x: x["published"], reverse=True)[:100]
    if not fresh_news:
        for item in old.get("news_sources") or []:
            published = iso(item.get("published"))
            if published and dt.datetime.fromisoformat(published.replace("Z", "+00:00")) >= cutoff:
                fresh_news.append(item)
        fresh_news = sorted(fresh_news, key=lambda x: x.get("published", ""), reverse=True)[:100]

    if successful == 0:
        raise SystemExit("All scoreboard sources failed; keeping the previous data.json unchanged.")
    updated["provider"] = "ESPN public API + BBC Sport + Sky Sports + The Guardian + Google News RSS"
    updated["timezone"] = "Asia/Muscat"
    updated["generated_at"] = NOW_ISO
    updated["leagues"] = leagues
    updated["news_sources"] = fresh_news
    updated["news_sources_updated_at"] = NOW_ISO if fresh_news else old.get("news_sources_updated_at")
    updated["news_errors"] = errors[:30]
    DATA_FILE.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {successful}/{len(LEAGUES)} leagues; {len(fresh_news)} recent news items; {len(errors)} warnings.")

if __name__ == "__main__":
    main()
