#!/usr/bin/env python3
"""Independent, keyless OpenLigaDB fallback for stale SLOOM365 football leagues.

This is a secondary source, not a replacement for ESPN. It only fills stale
leagues that OpenLigaDB actually covers, and never overwrites an existing
match with a different source's score or live clock.
"""
import json
import re
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data.json"
API = "https://api.openligadb.de"
HEADERS = {"User-Agent": "SLOOM365-BackupBot/1.0 (+https://sloom86ss.github.io/)", "Accept": "application/json"}
MAX_STALE_MINUTES = 7

ALIASES = {
    "soccer/eng.1": ["premier league", "english premier league"],
    "soccer/esp.1": ["laliga", "la liga", "primera division"],
    "soccer/ita.1": ["serie a", "italian serie a"],
    "soccer/ger.1": ["1 bundesliga", "bundesliga"],
    "soccer/fra.1": ["ligue 1"],
    "soccer/ksa.1": ["saudi pro league", "saudi professional league"],
    "soccer/por.1": ["primeira liga", "liga portugal"],
    "soccer/ned.1": ["eredivisie"],
    "soccer/bra.1": ["campeonato brasileiro serie a", "brasileirao serie a"],
    "soccer/arg.1": ["primera division", "liga profesional"],
    "soccer/usa.1": ["major league soccer", "mls"],
    "soccer/tur.1": ["super lig", "super lig"],
    "soccer/sco.1": ["scottish premiership", "premiership"],
    "soccer/jpn.1": ["j1 league", "j league"],
    "soccer/mex.1": ["liga mx"],
}

def now():
    return datetime.now(timezone.utc)

def iso(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def parse_dt(value, naive_zone=None):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo(naive_zone) if naive_zone else timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None

def norm(value):
    value = str(value or "").lower()
    value = value.replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "", value)

def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError("HTTP " + str(response.status))
        return json.loads(response.read().decode("utf-8"))

def league_age_minutes(league):
    stamp = parse_dt(league.get("updated_at"))
    return (now() - stamp).total_seconds() / 60 if stamp else None

def extract_score(match):
    results = match.get("matchResults") or []
    full = [x for x in results if str(x.get("resultTypeID")) == "2"]
    chosen = full[-1] if full else (results[-1] if results else None)
    if chosen:
        return chosen.get("pointsTeam1"), chosen.get("pointsTeam2")
    return None, None

def event_time(match):
    if match.get("matchDateTimeUTC"):
        return parse_dt(match.get("matchDateTimeUTC"))
    return parse_dt(match.get("matchDateTime"), "Europe/Berlin")

def convert_match(source, league_name, old_matches):
    team1 = source.get("team1") or {}
    team2 = source.get("team2") or {}
    home = str(team1.get("teamName") or "").strip()
    away = str(team2.get("teamName") or "").strip()
    if not home or not away:
        return None
    kickoff = event_time(source)
    if not kickoff:
        return None
    home_score, away_score = extract_score(source)
    finished = bool(source.get("matchIsFinished"))
    age = (now() - kickoff).total_seconds()
    if finished:
        status, detail = "post", "انتهت • المصدر الاحتياطي"
    elif -900 <= age <= 3 * 3600:
        status, detail = "in", "مباشر • المصدر الاحتياطي (دون دقيقة مؤكدة)"
    elif age < -900:
        status, detail = "pre", "لم تبدأ"
    else:
        return None

    # Do not replace a known ESPN match or its score/clock with community data.
    for old in old_matches:
        old_home = norm((old.get("home") or {}).get("name"))
        old_away = norm((old.get("away") or {}).get("name"))
        if old_home and old_away and ((old_home == norm(home) and old_away == norm(away)) or (old_home == norm(away) and old_away == norm(home))):
            return None

    if home_score is None or away_score is None:
        if status == "post":
            return None
    return {
        "id": "opendlb:" + str(source.get("matchID") or ""),
        "date": iso(kickoff),
        "time": iso(kickoff),
        "home": {"name": home, "logo": team1.get("teamIconUrl") or "", "score": str(home_score) if home_score is not None else None},
        "away": {"name": away, "logo": team2.get("teamIconUrl") or "", "score": str(away_score) if away_score is not None else None},
        "status": status,
        "detail": detail,
        "status_detail": detail,
        "status_short": detail,
        "period": None,
        "clock": "",
        "venue": (source.get("location") or ""),
        "broadcast": "",
        "data_source": "OpenLigaDB"
    }

def main():
    if not DATA_FILE.exists():
        raise SystemExit("data.json missing; backup will not create a new dataset")
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    leagues = data.get("leagues") or {}
    stale = []
    for key, league in leagues.items():
        age = league_age_minutes(league)
        if league.get("stale") or age is None or age > MAX_STALE_MINUTES:
            stale.append(key)
    try:
        available = get_json(API + "/getavailableleagues")
    except Exception as exc:
        print("OpenLigaDB discovery unavailable:", str(exc)[:180])
        data["backup_source_status"] = {"provider": "OpenLigaDB", "checked_at": iso(now()), "status": "unavailable", "error": str(exc)[:180]}
        DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
        return

    if not isinstance(available, list):
        print("OpenLigaDB returned an unexpected league catalogue.")
        return

    if not stale:
        print(f"Backup online: OpenLigaDB reachable; catalogue contains {len(available)} league-season entries. No fallback needed.")
        return

    print("Backup checking stale leagues:", ", ".join(stale))

    lookup = {}
    for entry in available:
        if not isinstance(entry, dict):
            continue
        name = norm(entry.get("leagueName"))
        for key, aliases in ALIASES.items():
            if name in {norm(alias) for alias in aliases}:
                lookup.setdefault(key, []).append(entry)

    filled = 0
    checked = 0
    unsupported = []
    errors = []
    for key in stale:
        candidates = lookup.get(key) or []
        if not candidates:
            unsupported.append(key)
            continue
        # Prefer the newest season exposed by the independent provider.
        candidates.sort(key=lambda x: int(str(x.get("leagueSeason") or 0)) if str(x.get("leagueSeason") or "").isdigit() else 0, reverse=True)
        selected = candidates[0]
        shortcut = selected.get("leagueShortcut")
        season = selected.get("leagueSeason")
        if not shortcut or not season:
            unsupported.append(key)
            continue
        checked += 1
        try:
            matches = get_json(f"{API}/getmatchdata/{shortcut}/{season}")
            if not isinstance(matches, list):
                raise RuntimeError("unexpected match list")
            old = leagues[key]
            old_matches = old.get("matches") or []
            additions = []
            for item in matches:
                converted = convert_match(item, old.get("name") or key, old_matches + additions)
                if converted:
                    additions.append(converted)
            if additions:
                old["matches"] = sorted(old_matches + additions, key=lambda x: x.get("date") or "")
                old["backup_provider"] = "OpenLigaDB"
                old["backup_updated_at"] = iso(now())
                old["stale"] = False
                old["updated_at"] = iso(now())
                filled += 1
                print(f"{key}: added {len(additions)} backup fixtures/results from OpenLigaDB")
            else:
                print(f"{key}: provider reachable, but no safe non-duplicate matches to add")
        except Exception as exc:
            errors.append(key + ": " + str(exc)[:140])
        time.sleep(0.25)

    if filled:
        data["generated_at"] = iso(now())
        data["backup_provider"] = "OpenLigaDB (independent community data; only supported stale leagues)"
    data["backup_source_status"] = {
        "provider": "OpenLigaDB",
        "checked_at": iso(now()),
        "status": "partial" if unsupported or errors else ("updated" if filled else "no_safe_matches"),
        "stale_leagues_checked": checked,
        "leagues_filled": filled,
        "unsupported_leagues": unsupported,
        "errors": errors[:10],
        "live_clock_note": "The free backup does not supply a verified live minute; no minute is invented."
    }
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Backup summary:", json.dumps(data["backup_source_status"], ensure_ascii=False))

if __name__ == "__main__":
    main()
