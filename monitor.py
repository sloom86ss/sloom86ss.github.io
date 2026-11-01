#!/usr/bin/env python3
"""SLOOM360 health monitor with ntfy push alerts and transition-only state."""
import json
import os
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
        if not isinstance(data.get("leagues"), dict) or not data["leagues"]:
            return False, "لا توجد بيانات دوريات"
        return True, "JSON سليم؛ عمر البيانات %.0f دقيقة" % max(0, age)
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
