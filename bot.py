#!/usr/bin/env python3
"""SLOOM TV data collector. ESPN public endpoints; failed feeds never erase good data."""
import json, os, time, re, urllib.request, urllib.error, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

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
}
NOW = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

RSS_FEEDS = [
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    ("Sky Sports", "https://www.skysports.com/rss/11095"),
    ("ESPN FC", "https://www.espn.com/espn/rss/soccer/news"),
    ("The Guardian", "https://www.theguardian.com/football/rss"),
    ("Google News", "https://news.google.com/rss/search?q=football%20soccer&hl=en-US&gl=US&ceid=US:en"),
    ("Google News", "https://news.google.com/rss/search?q=%D9%83%D8%B1%D8%A9%20%D8%A7%D9%84%D9%82%D8%AF%D9%85&hl=ar&gl=OM&ceid=OM:ar"),
    ("Google News", "https://news.google.com/rss/search?q=%D8%A7%D9%86%D8%AA%D9%82%D8%A7%D9%84%D8%A7%D8%AA%20%D9%83%D8%B1%D8%A9%20%D8%A7%D9%84%D9%82%D8%AF%D9%85&hl=ar&gl=SA&ceid=SA:ar"),
    ("Google News", "https://news.google.com/rss/search?q=%D8%A7%D9%84%D8%AF%D9%88%D8%B1%D9%8A%20%D8%A7%D9%84%D8%B3%D8%B9%D9%88%D8%AF%D9%8A%20%D9%83%D8%B1%D8%A9%20%D8%A7%D9%84%D9%82%D8%AF%D9%85&hl=ar&gl=SA&ceid=SA:ar"),
]

def parse_published(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except Exception:
        try:
            dt = parsedate_to_datetime(str(value))
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
def fetch_rss_news():
    """Collect attributed headlines from independent publisher RSS feeds."""
    items, errors = [], []
    for source, url in RSS_FEEDS:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; SLOOM-TV/2.0; RSS reader)",
                "Accept": "application/rss+xml, application/xml, text/xml"
            })
            with urllib.request.urlopen(req, timeout=15) as response:
                root = ET.fromstring(response.read())
            nodes = root.findall(".//item")
            if not nodes:
                nodes = root.findall(".//{*}entry")
            for node in nodes[:18]:
                def val(name):
                    found = node.find(name)
                    if found is None:
                        found = node.find("{*}" + name)
                    return (found.text or "").strip() if found is not None else ""
                title = val("title")
                link = val("link")
                if not link:
                    link_node = node.find("{*}link")
                    if link_node is not None:
                        link = link_node.attrib.get("href", "")
                description = val("description") or val("summary")
                description = re.sub(r"<[^>]+>", " ", description)
                description = re.sub(r"\s+", " ", description).strip()
                published = val("pubDate") or val("published") or val("updated")
                published_dt = parse_published(published)
                age = (datetime.now(timezone.utc) - published_dt).total_seconds() if published_dt else None
                allowed_hosts = {
                    "BBC Sport": ("bbc.co.uk", "bbc.com"),
                    "Sky Sports": ("skysports.com",),
                    "ESPN FC": ("espn.com",),
                    "The Guardian": ("theguardian.com",),
                    "Google News": ("news.google.com",)
                }
                host = (urlparse(link).hostname or '').lower()
                valid_link = any(host == domain or host.endswith('.' + domain) for domain in allowed_hosts[source])
                if title and link.startswith('https://') and valid_link and published_dt and 0 <= age <= 7 * 86400:
                    publisher = val("source") if source == "Google News" else ""
                    display_source = (publisher + " عبر Google News") if publisher else source
                    items.append({
                        "headline": title,
                        "description": description[:500],
                        "link": link,
                        "published": published_dt.isoformat(timespec="seconds").replace("+00:00", "Z"),
                        "fetched_at": NOW(),
                        "source": display_source,
                        "discovery_source": source,
                        "category": "transfers" if re.search(r"transfer|signs|signing|deal|loan|gossip|انتقال|صفقة|ضم|تعاقد", title, re.I) else "news"
                    })
        except Exception as exc:
            errors.append(source + ": " + str(exc)[:120])
    # Never reuse old RSS headlines when a publisher feed fails.
    unique = {}
    for item in items:
        unique[item["link"]] = item
    # Sort all publishers together before applying the cap, so early feeds
    # cannot crowd Google News and later sources out of the published list.
    return sorted(unique.values(), key=lambda item: item["published"], reverse=True)[:100], errors

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
        # Fetch three local calendar days (yesterday, today, tomorrow) in Oman time.
        local_today = datetime.now(ZoneInfo("Asia/Muscat")).date()
        events_by_id = {}
        for offset in (-1, 0, 1):
            day = (local_today + timedelta(days=offset)).strftime("%Y%m%d")
            payload = get_json(f"{BASE}/{key}/scoreboard?dates={day}")
            for event in payload.get("events", []):
                events_by_id[str(event.get("id", ""))] = event
        for event in events_by_id.values():
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
                "broadcast": ", ".join(x.get("names", [""])[0] for x in comp.get("broadcasts", []) if x.get("names")),
                "status_detail": status.get("detail", ""),
                "status_short": status.get("shortDetail", ""),
                "period": (comp.get("status") or {}).get("period"),
                "clock": (comp.get("status") or {}).get("displayClock", "")
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
                "published": article.get("published", ""),
                "fetched_at": NOW(),
                "category": "transfers" if re.search(r"transfer|signs|signing|deal|loan|gossip|انتقال|صفقة|ضم|تعاقد", (article.get("headline") or "") + " " + (article.get("description") or ""), re.I) else "news"
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

def send_ntfy(title, message, priority="default"):
    topic = os.getenv("NTFY_TOPIC", "").strip()
    if not topic:
        return False
    server = (os.getenv("NTFY_SERVER") or "https://ntfy.sh").rstrip("/")
    req = urllib.request.Request(
        server + "/" + topic,
        data=message.encode("utf-8"),
        headers={"Title": title, "Priority": priority, "Tags": "soccer"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return 200 <= response.status < 300
    except Exception as exc:
        print("ntfy notification failed:", str(exc)[:120])
        return False

def notify_match_changes(previous, current):
    old_matches = {}
    for league in (previous.get("leagues") or {}).values():
        for match in league.get("matches", []):
            if match.get("id"):
                old_matches[str(match["id"])] = match
    notices = []
    for league_id, league in (current.get("leagues") or {}).items():
        for match in league.get("matches", []):
            event_id = str(match.get("id", ""))
            old = old_matches.get(event_id)
            if not old:
                continue
            home, away = match.get("home") or {}, match.get("away") or {}
            old_home, old_away = old.get("home") or {}, old.get("away") or {}
            teams = (home.get("name", "Home") + " - " + away.get("name", "Away"))
            if str(home.get("score")) != str(old_home.get("score")) or str(away.get("score")) != str(old_away.get("score")):
                notices.append(("⚽ هدف / تحديث النتيجة", f"{teams}\n{home.get('score', '0')} - {away.get('score', '0')}\n{league.get('name', league_id)}"))
            elif old.get("status") != "in" and match.get("status") == "in":
                notices.append(("🔴 بدأت المباراة", f"{teams}\n{league.get('name', league_id)}"))
            elif not re.search(r"postpon|delay|suspend|abandon", str(old.get("status_detail", "")), re.I) and re.search(r"postpon|delay|suspend|abandon", str(match.get("status_detail", "")) + " " + str(match.get("detail", "")), re.I):
                notices.append(("⚠️ مباراة مؤجلة أو متوقفة", f"{teams}\n{match.get('status_detail') or match.get('detail') or 'لم يعلن السبب'}"))
            elif old.get("status") == "in" and match.get("status") == "post":
                notices.append(("🏁 انتهت المباراة", f"{teams}\n{home.get('score', '0')} - {away.get('score', '0')}"))
    for title, message in notices[:12]:
        send_ntfy(title, message, "high")
    if notices:
        print(f"Sent {min(len(notices), 12)} match notifications (if NTFY_TOPIC is configured).")

def main():
    path = os.path.join(os.path.dirname(__file__), "data.json")
    try:
        with open(path, encoding="utf-8") as f:
            previous = json.load(f)
    except Exception:
        previous = {}
    old_leagues = previous.get("leagues", previous if isinstance(previous, dict) else {})
    output = {"generated_at": NOW(), "timezone": "Asia/Muscat", "provider": "ESPN public API", "leagues": {}}
    output["news_sources"], output["news_errors"] = fetch_rss_news()
    output["news_sources_updated_at"] = NOW()
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
        send_ntfy("⚠️ تحديث بيانات SLOOM360 فشل", "لم ينجح تحديث أي مصدر لنتائج كرة القدم. يرجى فحص الموقع ومصادر البيانات.", "urgent")
        raise SystemExit("No scoreboard feed succeeded; keeping existing data.json unchanged.")
    notify_match_changes(previous, output)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Published {success}/{len(FEEDS)} current scoreboards; total matches={sum(len(x['matches']) for x in output['leagues'].values())}")

if __name__ == "__main__":
    main()
