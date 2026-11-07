#!/usr/bin/env python3
"""Generate Arabic, crawlable league and match pages from the current SLOOM365 data."""
import html
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data.json"
INDEX = ROOT / "index.html"
BASE = "https://sloom86ss.github.io"
OMAN = ZoneInfo("Asia/Muscat")
NOW = datetime.now(timezone.utc)

LEAGUE_DESCRIPTIONS = {
    "الدوري الإنجليزي الممتاز": "تابع جدول الدوري الإنجليزي الممتاز ومواعيد المباريات والنتائج المباشرة وأبرز مواجهات الأندية الإنجليزية.",
    "الدوري الإسباني": "تابع مباريات الدوري الإسباني ونتائج الفرق وترتيب المنافسة وأبرز مواجهات الكرة الإسبانية.",
    "الدوري الألماني": "تابع مباريات الدوري الألماني ومواعيد الجولات والنتائج وأخبار الأندية الألمانية.",
    "الدوري الإيطالي": "تابع جدول الدوري الإيطالي ونتائج المباريات ومواعيد المواجهات وأبرز أخبار الأندية.",
    "الدوري الفرنسي": "تابع مباريات الدوري الفرنسي والنتائج ومواعيد الجولات وأبرز مواجهات الأندية الفرنسية.",
    "دوري روشن السعودي": "تابع مباريات دوري روشن السعودي ونتائج الأندية ومواعيد المواجهات بتوقيت عُمان.",
    "دوري أبطال أوروبا": "تابع مباريات دوري أبطال أوروبا والنتائج ومواعيد المواجهات الأوروبية.",
    "دوري أبطال آسيا للنخبة": "تابع مباريات دوري أبطال آسيا للنخبة والنتائج ومواعيد الأندية الآسيوية.",
    "الدوري الهولندي": "تابع مباريات الدوري الهولندي والنتائج ومواعيد الجولات.",
    "الدوري البرتغالي": "تابع مباريات الدوري البرتغالي ونتائج الأندية ومواعيد المواجهات.",
    "الدوري التركي": "تابع مباريات الدوري التركي والنتائج ومواعيد الجولات.",
    "الدوري الياباني": "تابع مباريات الدوري الياباني والنتائج ومواعيد الأندية.",
    "الدوري الأمريكي": "تابع مباريات الدوري الأمريكي لكرة القدم والنتائج ومواعيد المواجهات.",
    "الدوري الأرجنتيني": "تابع مباريات الدوري الأرجنتيني والنتائج ومواعيد الجولات.",
    "الدوري المكسيكي": "تابع مباريات الدوري المكسيكي والنتائج ومواعيد المواجهات.",
    "الدوري الاسكتلندي": "تابع مباريات الدوري الاسكتلندي والنتائج ومواعيد الجولات.",
    "الدوري البرازيلي": "تابع مباريات الدوري البرازيلي والنتائج ومواعيد الأندية.",
}

DIGRAPHS = [
    ("sch", "ش"), ("sh", "ش"), ("ch", "تش"), ("th", "ث"), ("ph", "ف"),
    ("gh", "غ"), ("kh", "خ"), ("ck", "ك"), ("oo", "و"), ("ou", "و"),
    ("ee", "ي"), ("ea", "ي"), ("ai", "اي"), ("ay", "اي"), ("ow", "او"),
    ("tion", "شن"), ("qu", "ك"), ("ng", "نغ"),
]
LETTER = {
    "a":"ا","b":"ب","c":"ك","d":"د","e":"ي","f":"ف","g":"غ","h":"ه",
    "i":"ي","j":"ج","k":"ك","l":"ل","m":"م","n":"ن","o":"و","p":"ب",
    "q":"ك","r":"ر","s":"س","t":"ت","u":"و","v":"ف","w":"و","x":"كس",
    "y":"ي","z":"ز","á":"ا","é":"ي","í":"ي","ó":"و","ú":"و","ü":"و",
    "ñ":"ني","ø":"و","ö":"و","ä":"ا","ß":"س",
}

def esc(value):
    return html.escape(str(value or ""), quote=True)

def parse_club_names():
    source = INDEX.read_text(encoding="utf-8")
    match = re.search(r"const clubAr=(\{.*?\});const arTeam", source, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except Exception:
        return {}

CLUB_AR = parse_club_names()
EXTRA_CLUB_AR = {
    "Coventry City":"كوفنتري سيتي","Leeds United":"ليدز يونايتد","Hull City":"هال سيتي",
    "Ipswich Town":"إيبسويتش تاون","AFC Bournemouth":"بورنموث","Hamburg SV":"هامبورغ",
    "Borussia Mönchengladbach":"بوروسيا مونشنغلادباخ","SV Elversberg":"إلفيرسبرغ",
    "Mainz":"ماينز","FC Augsburg":"أوغسبورغ","SC Paderborn 07":"بادربورن",
    "Eintracht Frankfurt":"آينتراخت فرانكفورت","Werder Bremen":"فيردر بريمن",
    "FC Cologne":"كولن","Bayer Leverkusen":"باير ليفركوزن","SC Freiburg":"فرايبورغ",
    "1. FC Union Berlin":"يونيون برلين","TSG Hoffenheim":"هوفنهايم","Schalke 04":"شالكه",
    "Toulouse":"تولوز","AJ Auxerre":"أوكسير","Paris FC":"باريس إف سي","Troyes":"تروا",
    "Angers":"أنجيه","Le Havre AC":"لوهافر","Le Mans":"لومان","AS Monaco":"موناكو",
    "Alavés":"ألافيس","Málaga":"ملقا","Al Hazem":"الحزم","Neom SC":"نيوم",
    "Al Faisaly":"الفيصلي","Al Diriyah":"الدرعية","Venezia":"فينيتسيا","Udinese":"أودينيزي",
    "Cagliari":"كالياري","Frosinone":"فروزينوني","Parma":"بارما",
    "Barracas Central":"باراكاس سنترال","Racing Club":"راسينغ كلوب",
    "Deportivo Riestra":"ديبورتيفو ريسترا","San Lorenzo":"سان لورينزو",
    "Unión (Santa Fe)":"يونيون سانتا في","Vélez Sarsfield":"فيليز سارسفيلد",
    "Tigre":"تيغري","Sarmiento (Junín)":"سارمينتو","Gimnasia (Mendoza)":"خيمناسيا ميندوزا",
    "Talleres (Córdoba)":"تاليريس","Estudiantes de La Plata":"إستوديانتس",
    "Huracán":"هوراكان","Boca Juniors":"بوكا جونيورز","Rosario Central":"روزاريو سنترال",
    "Willem II":"فيلم تو","PEC Zwolle":"بي إي سي زفوله","Fortuna Sittard":"فورتونا سيتارد",
    "Telstar":"تيلستار","ADO Den Haag":"إيه دي أو لاهاي","Sparta Rotterdam":"سبارتا روتردام",
    "Excelsior":"إكسلسيور","Go Ahead Eagles":"غو أهيد إيغلز","Heerenveen":"هيرينفين",
    "FC Twente":"تفينتي","Ajax Amsterdam":"أياكس أمستردام","FC Groningen":"غرونينغن",
    "CF Montréal":"مونتريال","Vancouver Whitecaps":"فانكوفر وايتكابس",
    "Chicago Fire FC":"شيكاغو فاير","Columbus Crew":"كولومبوس كرو",
    "D.C. United":"دي سي يونايتد","New York City FC":"نيويورك سيتي",
    "FC Cincinnati":"سينسيناتي","Nashville SC":"ناشفيل","Inter Miami CF":"إنتر ميامي",
    "FC Famalicao":"فاماليكاو","Arouca":"أروكا","C.D. Nacional":"ناسيونال ماديرا",
    "Académico de Viseu":"أكاديميكو فيسيو","Casa Pia":"كاسا بيا","Moreirense":"موريرينسي",
    "Estoril":"إستوريل","Maritimo":"ماريتيمو","Santa Clara":"سانتا كلارا",
    "Estrela":"إستريلا أمادورا","Rio Ave":"ريو آفي","Braga":"سبورتينغ براغا",
    "Vitória":"فيتوريا","Fluminense":"فلومينينسي","Gaziantep FK":"غازي عنتاب",
    "Kasimpasa":"قاسم باشا","Eyupspor":"إيوب سبور","Kocaelispor":"كوجالي سبور",
    "Samsunspor":"سامسون سبور","Konyaspor":"قونية سبور","Amed SFK":"آمد سبور",
    "Goztepe":"غوزتبه","Istanbul Basaksehir":"باشاك شهير","Caykur Rizespor":"ريزه سبور",
    "Dundee United":"دندي يونايتد","Motherwell":"ماذرويل","St Johnstone":"سانت جونستون",
    "Dundee":"دندي","Aberdeen":"أبردين","Hibernian":"هيبرنيان",
    "St Mirren":"سانت ميرين","Heart of Midlothian":"هارتس","Falkirk":"فالكيرك",
    "Kilmarnock":"كيلمارنوك","Shimizu S-Pulse":"شيميزو إس بالس",
    "Tokyo Verdy 1969":"طوكيو فيردي","Nagoya Grampus":"ناغويا غرامبوس",
    "Yokohama F. Marinos":"يوكوهاما مارينوس","Fagiano Okayama":"فاجيانو أوكاياما",
    "Avispa Fukuoka":"أفيسبا فوكوكا","FC Tokyo":"إف سي طوكيو",
    "Kawasaki Frontale":"كاواساكي فرونتال","Machida Zelvia":"ماتشيدا زيلفيا",
    "Sanfrecce Hiroshima":"سانفريتشي هيروشيما","Urawa Red Diamonds":"أوراوا ريد دايموندز",
    "Atlético de San Luis":"أتلتيكو سان لويس","FC Juárez":"خواريز","Necaxa":"نيكاكسا",
    "Tijuana":"تيخوانا","Atlante":"أتلانتي","Atlas":"أطلس","Pachuca":"باتشوكا",
    "Tigres UANL":"تيغريس","Cruz Azul":"كروز أزول","Toluca":"تولوكا",
    "Monterrey":"مونتيري","Pumas UNAM":"بوماس",
}

def team_ar(name):
    name = str(name or "").strip()
    if name in EXTRA_CLUB_AR:
        return EXTRA_CLUB_AR[name]
    if name in CLUB_AR:
        return CLUB_AR[name]
    # Arabic phonetic fallback keeps generated sports pages Arabic-first.
    words = re.findall(r"[A-Za-zÀ-ÿ0-9]+|[^A-Za-zÀ-ÿ0-9]+", name)
    output = []
    for word in words:
        if not re.search(r"[A-Za-zÀ-ÿ]", word):
            output.append(word)
            continue
        w = word.lower()
        i, converted = 0, ""
        while i < len(w):
            found = False
            for src, dst in DIGRAPHS:
                if w.startswith(src, i):
                    converted += dst
                    i += len(src)
                    found = True
                    break
            if not found:
                converted += LETTER.get(w[i], w[i])
                i += 1
        output.append(converted)
    return "".join(output).strip() or "الفريق"

def parse_date(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def date_ar(value):
    dt = parse_date(value)
    if not dt:
        return "موعد غير محدد"
    local = dt.astimezone(OMAN)
    return local.strftime("%Y/%m/%d - %H:%M") + " بتوقيت عُمان"

def status_ar(match):
    status = match.get("status")
    if status == "in":
        return "مباشرة الآن"
    if status == "post":
        return "انتهت المباراة"
    if status == "pre":
        return "لم تبدأ بعد"
    return "موعد المباراة"

def score_text(match):
    home = (match.get("home") or {}).get("score")
    away = (match.get("away") or {}).get("score")
    if home is None or away is None:
        return "—"
    return f"{home} - {away}"

def slug(value):
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value)).strip("-").lower()

def shell(title, description, canonical, body, schema=None):
    schema_tag = ""
    if schema:
        schema_tag = '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False) + '</script>'
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="website"><meta property="og:locale" content="ar_OM">
<meta property="og:site_name" content="سلوم كورة 365"><meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}">
<meta name="theme-color" content="#100719">
<style>
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(ellipse at 50% -10%,#301044,#08050d 55%);color:#f8f2ff;font-family:Arial,Tahoma,sans-serif;line-height:1.9}}
main{{width:min(900px,100%);margin:auto;padding:24px 16px 60px}}header{{display:flex;align-items:center;gap:12px;margin-bottom:24px}}
.logo{{width:44px;height:44px;border-radius:14px;background:linear-gradient(145deg,#b7f34a,#7440a0);display:grid;place-items:center;color:#12091a;font-weight:900;font-size:19px}}
.brand{{font-weight:900;font-size:19px}}.brand small{{display:block;color:#b7a5c5;font-size:10px;letter-spacing:2px}}
h1{{font-size:clamp(25px,5vw,38px);line-height:1.4;margin:12px 0}}p{{color:#cbbbd6}}
.panel,.match{{background:#15101d;border:1px solid #392647;border-radius:17px;padding:15px;margin:12px 0}}
.match-top{{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;color:#c7b4d6;font-size:12px}}
.teams{{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:8px;margin:10px 0}}
.team{{font-weight:800;font-size:15px}}.away{{text-align:left}}.score{{font-size:20px;font-weight:900;color:#c9ff6c;white-space:nowrap}}
.meta{{font-size:12px;color:#bba9c9}}a{{color:#d8ff8b;text-decoration:none}}a:hover{{text-decoration:underline}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}}
footer{{margin-top:32px;border-top:1px solid #392647;padding-top:16px;color:#9d8baa;font-size:12px}}
@media(max-width:420px){{main{{padding:18px 12px 45px}}.team{{font-size:12px}}.panel,.match{{padding:12px}}}}
</style>
{schema_tag}
</head><body><main>
<header><div class="logo">365</div><div class="brand">سلوم كورة 365<small>SLOOM KORA 365</small></div></header>
{body}
<footer>© سلوم كورة 365 — متابعة عربية للمباريات والنتائج. <a href="{BASE}/">العودة إلى الصفحة الرئيسية</a></footer>
</main></body></html>'''

def match_card(match, league_name, match_url=None):
    home = team_ar((match.get("home") or {}).get("name"))
    away = team_ar((match.get("away") or {}).get("name"))
    href = match_url or "#"
    return f'''<article class="match">
<div class="match-top"><span>{esc(league_name)}</span><span>{esc(status_ar(match))}</span></div>
<div class="teams"><div class="team">{esc(home)}</div><div class="score">{esc(score_text(match))}</div><div class="team away">{esc(away)}</div></div>
<div class="meta">{esc(date_ar(match.get("date") or match.get("time")))} · {esc(match.get("venue") or "الملعب غير محدد")}</div>
<a href="{esc(href)}">تفاصيل المباراة</a>
</article>'''

def main():
    if not DATA.exists():
        raise SystemExit("data.json not found")
    data = json.loads(DATA.read_text(encoding="utf-8"))
    leagues = data.get("leagues") or {}
    league_dir = ROOT / "seo" / "leagues"
    match_dir = ROOT / "seo" / "matches"
    for directory in (league_dir, match_dir):
        directory.mkdir(parents=True, exist_ok=True)
        for old in directory.glob("*.html"):
            old.unlink()

    sitemap_urls = [
        (BASE + "/", NOW),
        (BASE + "/sloom360.html", NOW),
        (BASE + "/ai.html", NOW),
        (BASE + "/seo/leagues/", NOW),
    ]
    league_links = []
    match_count = 0
    for key, league in leagues.items():
        if not str(key).startswith("soccer/"):
            continue
        matches = league.get("matches") or []
        if not matches:
            continue
        league_name = league.get("name") or key
        league_slug = slug(key.split("/")[-1])
        league_url = f"{BASE}/seo/leagues/{league_slug}.html"
        ordered = sorted(matches, key=lambda item: parse_date(item.get("date") or item.get("time")) or datetime.max.replace(tzinfo=timezone.utc))
        cards = []
        for item in ordered:
            mid = slug(item.get("id"))
            if not mid:
                continue
            match_url = f"{BASE}/seo/matches/{mid}.html"
            dt = parse_date(item.get("date") or item.get("time"))
            # Keep match landing pages for live fixtures and the previous/following 14 days only.
            if dt and dt >= NOW - timedelta(days=2) and dt <= NOW + timedelta(days=14):
                home = team_ar((item.get("home") or {}).get("name"))
                away = team_ar((item.get("away") or {}).get("name"))
                title = f"{home} ضد {away} اليوم | {league_name} - سلوم كورة 365"
                description = f"تفاصيل مباراة {home} و{away}: الموعد {date_ar(item.get('date') or item.get('time'))}، النتيجة {score_text(item)}، الحالة {status_ar(item)}. متابعة عبر سلوم كورة 365."
                event = {
                    "@context": "https://schema.org",
                    "@type": "SportsEvent",
                    "name": f"{home} ضد {away}",
                    "startDate": dt.isoformat().replace("+00:00", "Z") if dt else None,
                    "sport": "Soccer",
                    "description": description,
                }
                if item.get("venue"):
                    event["location"] = {"@type":"Place","name":str(item["venue"])}
                body = f'''<p><a href="{BASE}/seo/leagues/{league_slug}.html">{esc(league_name)}</a></p>
<h1>{esc(home)} ضد {esc(away)}</h1>
<section class="panel"><div class="match-top"><span>{esc(league_name)}</span><strong>{esc(status_ar(item))}</strong></div>
<div class="teams"><div class="team">{esc(home)}</div><div class="score">{esc(score_text(item))}</div><div class="team away">{esc(away)}</div></div>
<p>{esc(date_ar(item.get("date") or item.get("time")))}</p>
<p>الملعب: {esc(item.get("venue") or "لم يعلن عن الملعب")}</p>
<p>تغطية المباراة والنتيجة عبر منصة سلوم كورة 365.</p></section>
<p><a href="{BASE}/">العودة إلى مباريات اليوم والنتائج المباشرة</a></p>'''
                page = shell(title, description, match_url, body, event)
                (match_dir / f"{mid}.html").write_text(page, encoding="utf-8")
                sitemap_urls.append((match_url, NOW))
                match_count += 1
            cards.append(match_card(item, league_name, match_url if dt and dt >= NOW - timedelta(days=2) and dt <= NOW + timedelta(days=14) else None))

        description = LEAGUE_DESCRIPTIONS.get(league_name, f"تابع جدول {league_name} ومواعيد المباريات والنتائج عبر سلوم كورة 365.")
        title = f"{league_name} | جدول المباريات والنتائج - سلوم كورة 365"
        body = f'''<p>كرة القدم · البطولات</p><h1>{esc(league_name)}</h1>
<p>{esc(description)}</p>
<div class="panel"><strong>مباريات البطولة المتاحة حالياً: {len(matches)}</strong><p>تعرض هذه الصفحة المباريات التي وصلت إلى مصدر البيانات، ويتم تحديثها مع تحديث بيانات الموقع.</p></div>
<h2>المباريات والنتائج</h2><div class="grid">{''.join(cards)}</div>
<p><a href="{BASE}/">شاهد جميع المباريات المباشرة وجدول اليوم عبر سلوم كورة 365</a></p>'''
        page = shell(title, description, league_url, body)
        (league_dir / f"{league_slug}.html").write_text(page, encoding="utf-8")
        sitemap_urls.append((league_url, NOW))
        league_links.append((league_name, league_url, len(matches)))

    directory_url = BASE + "/seo/leagues/"
    directory_body = "<p>دليل البطولات</p><h1>جداول الدوريات ومواعيد المباريات</h1><p>تابع البطولات العربية والعالمية ومواعيد المباريات والنتائج المتاحة عبر سلوم كورة 365.</p><div class=\"grid\">" + "".join(
        f'<section class="panel"><h2><a href="{esc(url)}">{esc(name)}</a></h2><p>مباريات متاحة: {count}</p><a href="{esc(url)}">جدول المباريات والنتائج</a></section>'
        for name, url, count in league_links
    ) + "</div><p><a href=\"" + BASE + "/\">العودة إلى الصفحة الرئيسية</a></p>"
    (league_dir / "index.html").write_text(shell("الدوريات وجداول المباريات | سلوم كورة 365", "دليل البطولات وجداول المباريات والنتائج المباشرة المتاحة في سلوم كورة 365.", directory_url, directory_body), encoding="utf-8")

    sitemap_urls.append((directory_url, NOW))
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, updated in sorted(set(sitemap_urls), key=lambda x: x[0]):
        sitemap.append(f"<url><loc>{html.escape(url)}</loc><lastmod>{updated.date().isoformat()}</lastmod></url>")
    sitemap.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")
    print(f"Generated {len(league_links)} league pages and {match_count} match pages.")
    print(f"Arabic club dictionary entries: {len(CLUB_AR)}")
    
if __name__ == "__main__":
    main()
