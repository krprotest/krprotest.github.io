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
    events.append(e)

events.sort(key=lambda e: (e["start_date"], e["event_id"]))
now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
os.makedirs(OUT_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, "events.json"), "w", encoding="utf-8") as f:
    json.dump({"generated_at": now, "count": len(events), "events": events}, f, ensure_ascii=False, indent=1)
# CSV 내려받기는 당분간 제공하지 않는다(자료 이용은 이메일 문의).
print(f"Approved {len(events)}건 내보냄, 건너뜀 {len(skipped)}건 {skipped}")
# 비공개 칸이 섞이지 않았는지 마지막으로 확인
leak = {"note", "raw_text", "contact_account", "review_status"} & set(events[0].keys() if events else [])
if leak:
    print("비공개 칸이 포함됨:", leak); sys.exit(1)
