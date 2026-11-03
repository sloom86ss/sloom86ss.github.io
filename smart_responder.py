#!/usr/bin/env python3
"""SLOOM365 smart data responder: diagnose stale ESPN feeds, retry once, and alert."""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

DATA_FILE = "data.json"
MAX_AGE_MINUTES = int(os.getenv("SMART_MAX_DATA_AGE_MINUTES", "20"))
LEAGUE_MAX_AGE_MINUTES = int(os.getenv("SMART_MAX_LEAGUE_AGE_MINUTES", "20"))


def parse_age_minutes(value):
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds() / 60
    except (TypeError, ValueError):
        return None


def load_data():
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def diagnose(data):
    problems, warnings = [], []
    age = parse_age_minutes(data.get("generated_at"))
    if age is None:
        problems.append("وقت generated_at مفقود أو غير صالح")
    elif age < -5:
        problems.append("وقت إنشاء البيانات في المستقبل")
    elif age > MAX_AGE_MINUTES:
        problems.append("البيانات قديمة: %.0f دقيقة" % age)

    leagues = data.get("leagues")
    if not isinstance(leagues, dict) or not leagues:
        problems.append("ملف البيانات لا يحتوي دوريات")
        leagues = {}

    stale, scoreboard_errors = [], []
    for key, league in leagues.items():
        if not isinstance(league, dict):
            problems.append("بيانات بطولة غير صالحة: " + str(key))
            continue
        name = league.get("name") or key
        if league.get("stale"):
            stale.append(name)
        league_age = parse_age_minutes(league.get("updated_at"))
        if league_age is None:
            stale.append(name + " (وقت التحديث مفقود)")
        elif league_age < -5:
            problems.append(name + ": وقت التحديث في المستقبل")
        elif league_age > LEAGUE_MAX_AGE_MINUTES:
            stale.append(name + " (%.0f دقيقة)" % league_age)

        errors = league.get("errors") or []
        for error in errors:
            message = str(error)
            if message.lower().startswith("scoreboard:"):
                scoreboard_errors.append(name + ": " + message)
            else:
                warnings.append(name + ": " + message)

        matches = league.get("matches")
        if not isinstance(matches, list):
            problems.append(name + ": قائمة المباريات غير صالحة")
            continue
        seen = set()
        for match in matches:
            if not isinstance(match, dict):
                warnings.append(name + ": سجل مباراة غير صالح")
                continue
            event_id = str(match.get("id") or "")
            if event_id and event_id in seen:
                warnings.append(name + ": مباراة مكررة " + event_id)
            if event_id:
                seen.add(event_id)
            if not match.get("date") or not (match.get("home") or {}).get("name") or not (match.get("away") or {}).get("name"):
                warnings.append(name + ": مباراة ينقصها التاريخ أو اسم أحد الفريقين")
            if match.get("status") == "in":
                home_score = (match.get("home") or {}).get("score")
                away_score = (match.get("away") or {}).get("score")
                if home_score is None or away_score is None:
                    warnings.append(name + ": مباراة مباشرة دون نتيجة مكتملة")

    if stale:
        problems.append("تحديثات دوريات متأخرة (%d): %s" % (len(stale), "، ".join(stale[:10])))
    if scoreboard_errors:
        problems.append("أخطاء في جلب جداول المباريات (%d): %s" % (
            len(scoreboard_errors), "؛ ".join(scoreboard_errors[:6])
        ))

    for error in data.get("news_errors") or []:
        warnings.append("الأخبار: " + str(error))

    return problems, warnings, age


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
    problems, warnings, age = diagnose(before)
    print("التشخيص الأولي:", json.dumps({
        "problems": problems, "warnings": warnings[:12], "age_minutes": age
    }, ensure_ascii=False))

    retried = False
    retry_exit_code = None
    if problems:
        print("اكتشف البوت خللاً في تحديث النتائج؛ سيعيد تشغيل جامع ESPN مرة واحدة.")
        result = subprocess.run([sys.executable, "-u", "bot.py"], timeout=600, check=False)
        retried = True
        retry_exit_code = result.returncode
        print("رمز انتهاء محاولة إعادة الجلب:", retry_exit_code)

    after = load_data()
    remaining, warnings_after, age_after = diagnose(after)
    report = {
        "retried_once": retried,
        "retry_exit_code": retry_exit_code,
        "remaining_problems": remaining,
        "warnings": warnings_after[:12],
        "data_age_minutes": age_after,
        "generated_at": after.get("generated_at"),
        "scoreboard_success_count": after.get("scoreboard_success_count"),
        "scoreboard_total_count": after.get("scoreboard_total_count"),
    }
    print("التقرير النهائي:", json.dumps(report, ensure_ascii=False))

    if remaining:
        lines = ["حالة بيانات SLOOM365 تحتاج متابعة بعد الفحص وإعادة المحاولة."]
        lines.append("المشكلات: " + "؛ ".join(remaining[:8]))
        if retried:
            lines.append("أعاد البوت محاولة الجلب مرة واحدة.")
        notify("\n".join(lines), "urgent")
    elif retried:
        notify("اكتشف البوت خللاً وأعاد جلب البيانات؛ الفحص النهائي سليم.", "default")
    elif warnings_after:
        print("تنبيهات غير حرجة (الأخبار أو تفاصيل ثانوية):", "؛ ".join(warnings_after[:8]))
    else:
        print("كل فحوصات البيانات سليمة.")


if __name__ == "__main__":
    main()
