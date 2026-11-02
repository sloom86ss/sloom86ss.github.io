#!/usr/bin/env python3
"""SLOOM365 safe auto-repair: only rebuild deterministic SEO support files."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
BASE = "https://sloom86ss.github.io"
PAGES = ["index.html", "sloom360.html", "ai.html"]

def main():
    missing = [name for name in PAGES if not (ROOT / name).is_file()]
    if missing:
        raise SystemExit("إصلاح متوقف: صفحات أساسية مفقودة: " + ", ".join(missing))

    data_path = ROOT / "data.json"
    if data_path.exists():
        try:
            data = json.loads(data_path.read_text(encoding="utf-8"))
            if not isinstance(data.get("leagues"), dict) or not data["leagues"]:
                print("تحذير: بيانات الدوريات غير صالحة؛ لن يتم اختراع أو استبدال بيانات المباريات.")
        except Exception as exc:
            print("تحذير: data.json غير صالح؛ لن يتم تغييره: " + str(exc))

    expected_urls = [BASE + "/", BASE + "/sloom360.html", BASE + "/ai.html"]
    sitemap_path = ROOT / "sitemap.xml"
    valid_sitemap = False
    if sitemap_path.exists():
        try:
            root = ET.fromstring(sitemap_path.read_text(encoding="utf-8"))
            current = [node.text or "" for node in root.iter() if node.tag.endswith("loc")]
            valid_sitemap = all(url in current for url in expected_urls)
        except Exception:
            valid_sitemap = False

    if not valid_sitemap:
        body = '<?xml version="1.0" encoding="UTF-8"?>\n'
        body += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        body += "".join("  <url><loc>" + url + "</loc></url>\n" for url in expected_urls)
        body += '</urlset>\n'
        sitemap_path.write_text(body, encoding="utf-8")
        print("تم إصلاح sitemap.xml تلقائياً.")

    robots_path = ROOT / "robots.txt"
    expected_robots = "User-agent: *\nAllow: /\nSitemap: " + BASE + "/sitemap.xml\n"
    current_robots = robots_path.read_text(encoding="utf-8") if robots_path.exists() else ""
    if current_robots != expected_robots:
        robots_path.write_text(expected_robots, encoding="utf-8")
        print("تم إصلاح robots.txt تلقائياً.")

    print("اكتمل الفحص الآمن. لم يتم تعديل HTML أو بيانات المباريات تلقائياً.")

if __name__ == "__main__":
    main()
