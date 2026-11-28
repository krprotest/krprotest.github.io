# -*- coding: utf-8 -*-
"""공개용 내보내기: Master_DB에서 review_status=Approved 행의 공개 칸만 뽑아
site/events.json 을 만든다. (홈페이지 구상 문서 2번 표 기준)

비공개 칸(note, raw_text, contact_account 등)은 아예 읽어서 쓰지 않는다.
location_spot 은 note 에 [자택] 태그가 있으면 지운다(개인 자택 앞 집회는 구 단위까지만).
publish 열(AE 이후)이 있고 값이 N 이면 Approved 라도 내보내지 않는다.
"""
import csv, json, os, sys
from datetime import datetime, timezone, timedelta
import gspread
from google.oauth2.service_account import Credentials

KST = timezone(timedelta(hours=9))
PUBLIC_COLS = ["event_id", "start_date", "end_date", "time_info", "event_title",
               "action_primary", "action_secondary", "mid_category",
               "organizers", "actor_type", "party_link", "party_name",
               "size_raw", "size_source", "size_scale",
               "region_sido", "region_sigungu", "location_spot",
               "issue_1", "issue_2", "issue_3", "target_entity",
               "source_media", "source_url", "source_type"]
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")

info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
sh = gspread.authorize(creds).open_by_key(os.environ["SHEET_ID"].strip())
vals = sh.worksheet("Master_DB").get_all_values()
head = vals[0]
idx = {h: i for i, h in enumerate(head)}
missing = [c for c in PUBLIC_COLS if c not in idx]
if missing:
    print("Master_DB에 없는 열:", missing); sys.exit(1)

# Actors 탭: 이름·별칭 → 행위자 유형 (주최가 여럿일 때 단체마다 유형을 붙이기 위해)
atype, canon = {}, {}
try:
    for ar in sh.worksheet("Actors").get_all_values()[1:]:
        ar = ar + [""] * 4
        if ar[0].strip() and ar[2].strip():
            for nm in [ar[0]] + [x for x in ar[1].replace(";", ",").split(",")]:
                if nm.strip():
                    atype.setdefault(nm.strip(), ar[2].strip())
                    canon.setdefault(nm.strip(), ar[0].strip())   # 별칭 → 대표 이름 (집계·필터용)
except Exception as ex:
    print("Actors 읽기 실패(유형 표시 생략):", ex)

events, skipped = [], []
for r in vals[1:]:
    r = r + [""] * len(head)
    if r[idx["review_status"]].strip() != "Approved":
        continue
    if "publish" in idx and r[idx["publish"]].strip().upper() == "N":
        skipped.append(r[idx["event_id"]]); continue
    if not r[idx["event_id"]].strip():
        skipped.append("(event_id 없음) " + r[idx["event_title"]][:30]); continue
    e = {c: r[idx[c]].strip() for c in PUBLIC_COLS}
    note = r[idx["note"]] if "note" in idx else ""
    if "[자택]" in note:
        e["location_spot"] = ""
    orgs = [o.strip() for o in e["organizers"].split(",") if o.strip()]
    if orgs:
        e["organizer_types"] = [atype.get(o, "") for o in orgs]
        e["organizers_canon"] = [canon.get(o, o) for o in orgs]
        if e["organizer_types"] and not e["organizer_types"][0]:
            e["organizer_types"][0] = e["actor_type"]
    events.append(e)

events.sort(key=lambda e: (e["start_date"], e["event_id"]))
now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
os.makedirs(OUT_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, "events.json"), "w", encoding="utf-8") as f:
    json.dump({"generated_at": now, "count": len(events), "events": events}, f, ensure_ascii=False, indent=1)
# RSS 피드: 최근 공개 사건 50건
SITE = "https://krprotest.github.io/"
AL = {"01":"성명·시국선언","02":"기자회견","03":"서명·청원","04":"고소·고발·진정","05":"피케팅·선전전","06":"항의방문","07":"집회·행진",
      "08":"1인시위","09":"단식·삭발·혈서","10":"농성·점거·방해","11":"물리적 충돌·파괴","12":"세미나·토론회","13":"비대면 집단항의","14":"분신·자해","15":"불매·거부"}
def _x(t):
    return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
items = []
for ev in sorted(events, key=lambda x: (x["start_date"], x["event_id"]), reverse=True)[:50]:
    place = " ".join(x for x in (ev["region_sido"], ev["region_sigungu"], ev["location_spot"]) if x and x != "비해당")
    desc = " · ".join(x for x in (AL.get(ev["action_primary"], ev["action_primary"]), ev["organizers"], place, ev["start_date"]) if x)
    try:
        pub = datetime.strptime(ev["start_date"], "%Y-%m-%d").replace(tzinfo=KST).strftime("%a, %d %b %Y 09:00:00 +0900")
    except ValueError:
        pub = ""
    link = SITE + "?id=" + ev["event_id"]
    items.append(f"<item><title>{_x(ev['event_title'])}</title><link>{link}</link><guid>{link}</guid>"
                 f"<pubDate>{pub}</pubDate><description>{_x(desc)}</description></item>")
with open(os.path.join(OUT_DIR, "feed.xml"), "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
            f"<title>한국 보수·우파 항의행동 데이터베이스</title><link>{SITE}</link>"
            f"<description>새로 공개된 사건</description><lastBuildDate>{datetime.now(KST).strftime('%a, %d %b %Y %H:%M:%S +0900')}</lastBuildDate>"
            + "".join(items) + "</channel></rss>")
# CSV 내려받기는 당분간 제공하지 않는다(자료 이용은 이메일 문의).
print(f"Approved {len(events)}건 내보냄, 건너뜀 {len(skipped)}건 {skipped}")
# 비공개 칸이 섞이지 않았는지 마지막으로 확인
leak = {"note", "raw_text", "contact_account", "review_status"} & set(events[0].keys() if events else [])
if leak:
    print("비공개 칸이 포함됨:", leak); sys.exit(1)
