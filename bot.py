import json
import requests

LEAGUES = ["uefa.champions", "eng.1", "esp.1", "ita.1"]
all_data = {}

for league in LEAGUES:
    try:
        # جلب المباريات
        m_res = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard").json()
        # جلب الأخبار
        n_res = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/news").json()
        
        all_data[league] = {
            "matches": m_res.get("events", []),
            "news": n_res.get("articles", [])[:5]
        }
        print(f"✅ تم جلب بيانات {league}")
    except Exception as e:
        print(f"❌ خطأ في {league}: {e}")

# حفظ كل البيانات في ملف واحد ليقرأه الموقع
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)