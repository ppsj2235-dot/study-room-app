# -*- coding: utf-8 -*-
import json
from datetime import date

from db import db_cursor
from content_bank import suggest_director_message, suggest_quote

DEFAULT_ACADEMY_TAGLINE = "기초부터 탄탄하게, 끝까지 함께."

DEFAULT_GROWTH_ITEMS = [
    {"title": "이번 달 집중 목표", "desc": "이번 달 집중 목표를 입력해주세요."},
    {"title": "학습 목표 설정", "desc": "학습 목표를 입력해주세요."},
    {"title": "성장 체크", "desc": "성장 체크 항목을 입력해주세요."},
]

DEFAULT_TIP_ITEMS = [
    "틀린 문제는 꼭 오답노트에 기록하기",
    "풀이는 단계를 나눠서 작성하기",
    "한 문제를 설명해 보는 연습하기",
]

DEFAULT_HOME_ITEMS = [
    {"title": "숙제 확인", "desc": "매일 숙제와 학습 내용을 확인해 주세요. 과정보다 스스로 끝까지 해결하는 과정을 함께 격려해 주세요."},
    {"title": "학습 준비물", "desc": "교재, 연필, 지우개 등 기본 준비물을 아이가 직접 챙기는 습관을 길러주세요."},
    {"title": "연락 및 일정", "desc": "결석이나 지각, 일정 변경 시 수업 시작 전에 미리 연락 부탁드립니다."},
    {"title": "응원 한마디", "desc": "“오늘도 수고했어.” 라는 한마디가 아이에게 가장 큰 힘이 됩니다."},
]

DEFAULT_TUITION = {
    "period": "",
    "account": "",
    "note": "",
    "qr_label": "QR코드",
    "qr_image_path": None,
}

DEFAULT_CONTACT = {"phone": "", "address": "", "note": ""}


def _row_to_dict(row):
    if row is None:
        return None
    data = json.loads(row["data"])
    data["id"] = row["id"]
    data["year"] = row["year"]
    data["month"] = row["month"]
    data["created_at"] = row["created_at"]
    data["updated_at"] = row["updated_at"]
    return data


def get_newsletter(newsletter_id):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM newsletters WHERE id = ?", (newsletter_id,))
        return _row_to_dict(cur.fetchone())


def list_newsletters():
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM newsletters ORDER BY year DESC, month DESC, id DESC"
        )
        return [_row_to_dict(r) for r in cur.fetchall()]


def get_latest_newsletter():
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM newsletters ORDER BY year DESC, month DESC, id DESC LIMIT 1"
        )
        return _row_to_dict(cur.fetchone())


def build_default_data(academy_name, year, month, carry_over=None):
    """새 알림장 기본값. carry_over가 있으면 '고정' 항목을 이전 값에서 이어받는다."""
    base = {
        "academy_name": academy_name,
        "tagline": DEFAULT_ACADEMY_TAGLINE,
        "notices": ["", "", ""],
        "tuition": dict(DEFAULT_TUITION),
        "growth_items": [dict(x) for x in DEFAULT_GROWTH_ITEMS],
        "tip_items": list(DEFAULT_TIP_ITEMS),
        "home_items": [dict(x) for x in DEFAULT_HOME_ITEMS],
        "contact": dict(DEFAULT_CONTACT),
        "extra_closed_days": [],
        "extra_open_days": [],
    }

    if carry_over:
        for key in ("tagline", "notices", "tuition", "growth_items", "tip_items", "home_items", "contact"):
            if carry_over.get(key):
                base[key] = carry_over[key]

    msg = suggest_director_message(year, month)
    quote_text, quote_author = suggest_quote(year, month)
    base["director_message"] = msg
    base["quote_text"] = quote_text
    base["quote_author"] = quote_author

    return base


def create_newsletter(year, month, data):
    payload = dict(data)
    payload.pop("id", None)
    payload.pop("year", None)
    payload.pop("month", None)
    payload.pop("created_at", None)
    payload.pop("updated_at", None)
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO newsletters (year, month, data) VALUES (?, ?, ?)",
            (year, month, json.dumps(payload, ensure_ascii=False)),
        )
        return cur.lastrowid


def update_newsletter(newsletter_id, data):
    payload = dict(data)
    payload.pop("id", None)
    payload.pop("year", None)
    payload.pop("month", None)
    payload.pop("created_at", None)
    payload.pop("updated_at", None)
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE newsletters SET data = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(payload, ensure_ascii=False), newsletter_id),
        )


def delete_newsletter(newsletter_id):
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM newsletters WHERE id = ?", (newsletter_id,))


def parse_day_list(text):
    """'3, 7, 15' 같은 문자열을 [3,7,15] 정수 리스트로."""
    if not text:
        return []
    out = []
    for part in text.replace("\n", ",").split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out
