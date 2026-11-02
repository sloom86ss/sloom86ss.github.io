#!/usr/bin/env python3
"""SLOOM360 health monitor with ntfy push alerts and transition-only state."""
import json
import os
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
from datetime import datetime, timezone

BASE = os.getenv("SLOOM_SITE_URL", "https://sloom86ss.github.io").rstrip("/")
STATE_FILE = "monitor_state.json"
MAX_DATA_AGE_MINUTES = int(os.getenv("MAX_DATA_AGE_MINUTES", "100"))

def get_url(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "SLOOM360-Monitor/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.status, response.read()

def check_page(url):
    try:
        status, _ = get_url(url)
        return status == 200, "HTTP " + str(status)
    except urllib.error.HTTPError as exc:
        return False, "HTTP " + str(exc.code)
    except Exception as exc:
        return False, str(exc)[:160]

def check_chat_asset():
    try:
        status, raw = get_url(BASE + "/chat.js")
        if status != 200:
            return False, "HTTP " + str(status)
        source = raw.decode("utf-8", errors="replace")
        required = ("async function getData()", "form.addEventListener", "/data.json")
        missing = [item for item in required if item not in source]
        if missing:
            return False, "ملف الشات ناقص مكونات التشغيل: " + ", ".join(missing)
        return True, "ملف الشات متاح ويقرأ بيانات الموقع"
    except Exception as exc:
        return False, "تعذر فحص ملف الشات: " + str(exc)[:140]

def check_seo_files():
    try:
        _, sitemap = get_url(BASE + "/sitemap.xml")
        root = ET.fromstring(sitemap)
        urls = [node.text or "" for node in root.iter() if node.tag.endswith("loc")]
        required = [BASE + "/", BASE + "/sloom360.html", BASE + "/ai.html"]
        missing = [url for url in required if url not in urls]
        if missing:
            return False, "روابط ناقصة في sitemap.xml: " + ", ".join(missing)
        _, robots = get_url(BASE + "/robots.txt")
        text = robots.decode("utf-8", errors="replace")
        if "Sitemap: " + BASE + "/sitemap.xml" not in text:
            return False, "رابط sitemap غير موجود في robots.txt"
        return True, "sitemap.xml وrobots.txt سليمان"
    except Exception as exc:
        return False, "خطأ في ملفات SEO: " + str(exc)[:140]

def check_data():
    try:
        status, raw = get_url(BASE + "/data.json")
        if status != 200:
            return False, "HTTP " + str(status)
        data = json.loads(raw.decode("utf-8"))
        generated = data.get("generated_at")
        if not generated:
            return False, "generated_at غير موجود"
        stamp = datetime.fromisoformat(generated.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds() / 60
        if age < -5:
            return False, "وقت إنشاء البيانات في المستقبل"
        if age > MAX_DATA_AGE_MINUTES:
            return False, "البيانات قديمة منذ %.0f دقيقة" % age
        leagues = data.get("leagues")
        if not isinstance(leagues, dict) or not leagues:
            return False, "لا توجد بيانات دوريات"
        match_count = sum(len(league.get("matches", [])) for league in leagues.values()
                          if isinstance(league, dict) and isinstance(league.get("matches", []), list))
        news = data.get("news_sources", [])
        if not isinstance(news, list):
            return False, "قائمة الأخبار غير صالحة"
        return True, "JSON سليم؛ %d بطولة؛ %d مباراة؛ %d خبر؛ عمر البيانات %.0f دقيقة" % (
            len(leagues), match_count, len(news), max(0, age))
    except Exception as exc:
        return False, "تعذر قراءة data.json: " + str(exc)[:140]

def notify(title, message, priority="default"):
    topic = os.getenv("NTFY_TOPIC", "").strip()
    if not topic:
        print("NTFY_TOPIC is not configured; mobile alerts are disabled.")
        return
    server = (os.getenv("NTFY_SERVER") or "https://ntfy.sh").rstrip("/")
    req = urllib.request.Request(
        server + "/" + topic,
        data=message.encode("utf-8"),
        headers={"Title": title, "Priority": priority, "Tags": "warning"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            print("ntfy:", response.status)
    except Exception as exc:
        print("ntfy failed:", str(exc)[:120])

def main():
    checks = {
        "homepage": check_page(BASE + "/"),
        "football_page": check_page(BASE + "/sloom360.html"),
        "ai_page": check_page(BASE + "/ai.html"),
        "chat_asset": check_chat_asset(),
        "seo_files": check_seo_files(),
        "sports_data": check_data(),
    }
    failed = [name + " (" + detail + ")" for name, (ok, detail) in checks.items() if not ok]
    healthy = not failed

    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            previous = json.load(f)
    except Exception:
        previous = {}

    previous_health = previous.get("healthy")
    if failed and previous_health is not False:
        notify("⚠️ SLOOM360: الموقع يواجه عطلاً",
               "تعذر اجتياز الفحوصات: " + "؛ ".join(failed), "urgent")
    elif healthy and previous_health is False:
        notify("✅ SLOOM360 عاد للعمل",
               "عادت الصفحات والبيانات إلى الحالة السليمة وتم التحقق منها.", "default")

    # Persist only the first result or a health-state transition to avoid noisy commits.
    if previous_health is None or previous_health != healthy:
        state = {
            "healthy": healthy,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "checks": {name: {"ok": ok, "detail": detail} for name, (ok, detail) in checks.items()},
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    print(json.dumps({
        "healthy": healthy,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": {name: {"ok": ok, "detail": detail} for name, (ok, detail) in checks.items()},
    }, ensure_ascii=False))
    if failed:
        raise SystemExit("Health check failed")

if __name__ == "__main__":
    main()
