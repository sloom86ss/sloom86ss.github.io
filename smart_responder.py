#!/usr/bin/env python3
"""SLOOM365 Smart Responder: diagnose stale feeds, retry once, and alert."""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

DATA_FILE = "data.json"
MAX_AGE_MINUTES = int(os.getenv("SMART_MAX_DATA_AGE_MINUTES", "45"))

def load_data():
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)

def diagnose(data):
    problems = []
    generated = data.get("generated_at")
    age = None
    try:
        stamp = datetime.fromisoformat(generated.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds() / 60
        if age < -5:
            problems.append("وقت إنشاء البيانات في المستقبل")
        elif age > MAX_AGE_MINUTES:
            problems.append("البيانات قديمة: %.0f دقيقة" % age)
    except Exception:
        problems.append("وقت generated_at مفقود أو غير صالح")

    leagues = data.get("leagues")
    if not isinstance(leagues, dict) or not leagues:
        problems.append("ملف البيانات لا يحتوي دوريات")
        leagues = {}

    stale = []
    for key, league in leagues.items():
        if league.get("stale") or not league.get("updated_at"):
            stale.append(league.get("name", key))
    if stale:
        problems.append("مصادر دوريات متعثرة (%d): %s" % (len(stale), "، ".join(stale[:8])))

    feed_errors = []
    for key, league in leagues.items():
        for error in league.get("errors", []):
            feed_errors.append("%s: %s" % (league.get("name", key), error))
    for error in data.get("news_errors", []):
        feed_errors.append("الأخبار: " + str(error))
    return problems, feed_errors, age

def notify(message, priority="high"):
    topic = os.getenv("NTFY_TOPIC", "").strip()
    if not topic:
        print("NTFY_TOPIC غير مضبوط؛ لم يرسل تنبيه الهاتف.")
        return False
    server = (os.getenv("NTFY_SERVER") or "https://ntfy.sh").rstrip("/")
    req = urllib.request.Request(
        server + "/" + topic,
        data=message.encode("utf-8"),
        headers={"Title": "SLOOM365 | تقرير البوت الذكي", "Priority": priority, "Tags": "warning,robot"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            print("ntfy notification HTTP", response.status)
            return 200 <= response.status < 300
    except Exception as exc:
        print("تعذر إرسال التنبيه:", str(exc)[:160])
        return False

def main():
    before = load_data()
    problems, feed_errors, age = diagnose(before)
    print("التشخيص الأولي:", json.dumps({"problems": problems, "feed_errors": feed_errors[:15], "age_minutes": age}, ensure_ascii=False))

    retried = False
    if problems:
        print("يوجد خلل؛ سأعيد تشغيل جامع البيانات مرة واحدة فقط.")
        result = subprocess.run([sys.executable, "-u", "bot.py"], timeout=600)
        retried = True
        if result.returncode == 0:
            print("انتهت محاولة إعادة الجلب بنجاح.")
        else:
            print("فشلت محاولة إعادة الجلب برمز:", result.returncode)

    after = load_data()
    remaining, errors_after, age_after = diagnose(after)
    report = {
        "retried_once": retried,
        "remaining_problems": remaining,
        "source_errors": errors_after[:15],
        "data_age_minutes": age_after,
        "generated_at": after.get("generated_at"),
    }
    print("التقرير النهائي:", json.dumps(report, ensure_ascii=False))

    if remaining or errors_after:
        lines = ["حالة بيانات SLOOM365 تحتاج متابعة."]
        if remaining:
            lines.append("المشكلات: " + "؛ ".join(remaining))
        if errors_after:
            lines.append("أخطاء المصادر: " + "؛ ".join(errors_after[:8]))
        if retried:
            lines.append("أعاد البوت محاولة الجلب مرة واحدة.")
        notify("\n".join(lines), "urgent" if remaining else "high")
    elif retried:
        notify("تمت إعادة جلب البيانات بعد اكتشاف خلل، والفحص النهائي سليم.", "default")
    else:
        print("كل الفحوصات سليمة؛ لا حاجة لأي إجراء.")

if __name__ == "__main__":
    main()
