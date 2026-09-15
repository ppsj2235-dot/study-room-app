# -*- coding: utf-8 -*-
"""알림장 축소판(명언/원장 한마디/학습TIP 삭제, 성장 포인트 가로화) 미리보기 렌더링.
아직 배포 전 - 로컬 확인용 이미지만 생성합니다."""
import os
import models_newsletter as mn
from newsletter_render import render_flyer_png

OUT_DIR = "/tmp/newsletter_preview"
os.makedirs(OUT_DIR, exist_ok=True)

THEMES_TO_CHECK = ["green", "cream_mustard"]

for theme in THEMES_TO_CHECK:
    data = mn.build_default_data("느루 공부방", 2026, 10)
    data["theme"] = theme
    data["year"] = 2026
    data["month"] = 10
    data["notices"] = [
        "10월 21일(수)은 개교기념일로 휴무입니다.",
        "10월 넷째 주 월간 평가 시험이 진행됩니다.",
        "겨울방학 특강 신청은 11월 초 안내드릴 예정입니다.",
    ]
    data["tuition"] = {
        "period": "매월 1일 ~ 5일",
        "account": "국민은행 123456-04-123456 (예금주: 박성재)",
        "note": "카카오페이로도 납부하실 수 있습니다.",
        "qr_label": "QR코드",
        "qr_image_data": None,
    }
    data["contact"] = {
        "phone": "010-1234-5678",
        "address": "경기도 김포시 고촌읍 수기로 136 225동 405호",
        "note": "수업 관련 문의는 문자로 남겨주시면 확인 후 연락드리겠습니다.",
    }
    out_path = os.path.join(OUT_DIR, f"newsletter_short_{theme}.png")
    render_flyer_png(data, out_path, scale=2)
    print("rendered:", out_path)
