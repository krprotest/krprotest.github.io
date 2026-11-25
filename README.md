# 한국 보수·우파 항의행동 데이터베이스 · Korean Right-Wing Protest Tracker

우파 행위자의 집합적 항의행동 사건 데이터베이스의 공개 사이트입니다.
매일 아침 검수가 끝난(Approved) 사건만 `site/events.json`으로 내보내 GitHub Pages에 올립니다.

- `site/index.html` — 사이트 본체 (사건 목록·추이·통계·방법론·소개·English)
- `scripts/export_public.py` — 공개 칸만 뽑아 events.json을 만드는 스크립트
- `.github/workflows/publish.yml` — 매일 06:40 KST 자동 발행 + 수동 실행

자료 이용·인용·정정 문의: rightactivitytracking@gmail.com
