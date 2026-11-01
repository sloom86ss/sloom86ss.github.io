#!/usr/bin/env python3
"""SLOOM360 health monitor with optional ntfy push alerts."""
import json, os, urllib.request, urllib.error
from datetime import datetime, timezone

BASE = os.getenv("SLOOM_SITE_URL", "https://sloom86ssgithubio.vercel.app").rstrip("/")
STATE_FILE = "monitor_state.json"

def check(url, expected=(200,)):
    req = urllib.request.Request(url, headers={"User-Agent": "SLOOM360-Monitor/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status in expected, "HTTP " + str(response.status)
    except urllib.error.HTTPError as exc:
        return exc.code in expected, "HTTP " + str(exc.code)
    except Exception as exc:
        return False, str(exc)[:160]

def notify(title, message, priority="default"):
    topic = os.getenv("NTFY_TOPIC", "").strip()
    if not topic:
        print("NTFY_TOPIC is not configured; mobile alerts are disabled.")
        return
    server = os.getenv("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    req = urllib.request.Request(server + "/" + topic, data=message.encode("utf-8"),
        headers={"Title": title, "Priority": priority, "Tags": "warning"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            print("ntfy:", response.status)
    except Exception as exc:
        print("ntfy failed:", str(exc)[:120])

def main():
    checks = {
        "homepage": check(BASE + "/"),
        "football_page": check(BASE + "/sloom360.html"),
        "sports_data": check(BASE + "/data.json"),
        "chat_api": check(BASE + "/api/chat", (405,))
    }
    failed = [name + " (" + detail + ")" for name, (ok, detail) in checks.items() if not ok]
    current = {"healthy": not failed, "checked_at": datetime.now(timezone.utc).isoformat(),
               "checks": {name: {"ok": ok, "detail": detail} for name, (ok, detail) in checks.items()}}
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            previous = json.load(f)
    except Exception:
        previous = {}
    if failed and previous.get("healthy") is not False:
        notify("⚠️ SLOOM360: الموقع يواجه عطلاً", "تعذر الوصول إلى: " + ", ".join(failed), "urgent")
    elif not failed and previous.get("healthy") is False:
        notify("✅ SLOOM360 عاد للعمل", "تم التحقق من الصفحة الرئيسية وصفحة كرة القدم والبيانات وواجهة البوت.", "default")
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    print(json.dumps(current, ensure_ascii=False))
    if failed:
        raise SystemExit("Health check failed")

if __name__ == "__main__":
    main()
