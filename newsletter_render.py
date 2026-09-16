# -*- coding: utf-8 -*-
"""알림장(월간 소식지) HTML 렌더링 + 이미지 변환."""

import base64
import os

from jinja2 import Environment, FileSystemLoader

import icons
from newsletter_calendar import build_calendar
from newsletter_themes import DEFAULT_THEME, THEMES, get_theme_colors

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static", "newsletter")

MONTH_ENG = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

_env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, "templates")))


def _file_to_data_uri(path):
    if not path or not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    mime = "png" if ext == "png" else ("jpeg" if ext in ("jpg", "jpeg") else ext)
    return f"data:image/{mime};base64,{b64}"


def _themed_illust_path(base_name, theme_key):
    """테마별로 미리 만들어둔 삽화(캐릭터 옷/가방 색 등)가 있으면 그걸 쓰고,
    없으면(기본 그린 테마 포함) 원본 파일을 그대로 씁니다."""
    if theme_key and theme_key != DEFAULT_THEME:
        themed_path = os.path.join(STATIC_DIR, f"{base_name}_{theme_key}.png")
        if os.path.exists(themed_path):
            return themed_path
    return os.path.join(STATIC_DIR, f"{base_name}.png")


def _build_theme_assets():
    """관리자 편집 화면에서 테마를 고를 때 저장 없이도 미리보기(iframe)를
    바로 갱신할 수 있도록, 테마별 색상값 + 삽화(data URI)를 미리 한 번에
    계산해둔다. 테마 개수(11개)가 적고 이미지 용량도 작아서 서버 시작 시
    한 번만 계산해도 충분하다."""
    assets = {}
    for key, colors in THEMES.items():
        assets[key] = {
            "colors": colors,
            "topright": _file_to_data_uri(_themed_illust_path("illust_topright", key)),
            "backpack": _file_to_data_uri(_themed_illust_path("illust_backpack", key)),
        }
    return assets


THEME_ASSETS = _build_theme_assets()

# 수강료 QR코드는 매달 바뀌는 게 아니라 공부방이 항상 쓰는 고정 결제 QR이라서,
# 관리자가 이 달에 QR을 따로 올리지 않아도(=DB의 tuition.qr_image_data가 비어있어도)
# 모든 알림장에 기본값으로 항상 나오도록 코드에 기본 QR을 base64로 심어둡니다.
# (그래도 특정 달만 QR을 다르게 쓰고 싶으면, 관리자 편집 화면에서 그 달에만
#  QR 이미지를 따로 올리면 그 달은 그 이미지가 기본� 대신 우선 사용됩니다.)
_DEFAULT_QR_B64 = (
    "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"
)
DEFAULT_QR_DATA_URI = "data:image/png;base64," + _DEFAULT_QR_B64


def render_flyer_html(newsletter):
    """newsletter: dict (see models_newsletter.default_newsletter_data 구조)"""
    year = newsletter["year"]
    month = newsletter["month"]

    cal = build_calendar(
        year,
        month,
        extra_closed_days=newsletter.get("extra_closed_days"),
        extra_open_days=newsletter.get("extra_open_days"),
    )

    qr_data_uri = newsletter.get("tuition", {}).get("qr_image_data")
    theme_key = newsletter.get("theme") or DEFAULT_THEME
    theme_colors = get_theme_colors(theme_key)

    ctx = {
        "theme_key": theme_key,
        "theme_colors": theme_colors,
        "academy_name": newsletter["academy_name"],
        "year": year,
        "month": month,
        "month_eng": MONTH_ENG[month],
        "tagline": newsletter.get("tagline", "기초부터 탄탄하게, 끝까지 함께."),
        "weekday_labels": cal["weekday_labels"],
        "weeks": cal["weeks"],
        "notices": newsletter.get("notices") or ["원장님이 여기에 공지사항을 입력해주세요."],
        "tuition": {
            "period": newsletter.get("tuition", {}).get("period", ""),
            "account": newsletter.get("tuition", {}).get("account", ""),
            "note": newsletter.get("tuition", {}).get("note", ""),
            "qr_label": newsletter.get("tuition", {}).get("qr_label", "QR코드"),
            # 이 달에 관리자가 직접 올린 QR(qr_image_data)이 있으면 그걸 쓰고,
            # 없으면 항상 고정으로 나오는 기본 QR(DEFAULT_QR_DATA_URI)을 씀 -
            # 즉 QR은 특정 달에만 나오는 게 아니라 모든 알림장에 기본으로 항상 나옴.
            "qr_image": qr_data_uri or DEFAULT_QR_DATA_URI,
        },
        "growth_items": newsletter.get("growth_items", []),
        "tip_items": newsletter.get("tip_items", []),
        "director_message": newsletter.get("director_message", ""),
        "home_items": newsletter.get("home_items", []),
        "quote_text": newsletter.get("quote_text", ""),
        "quote_author": newsletter.get("quote_author", ""),
        "contact": newsletter.get("contact", {}),
        "illust_topright": _file_to_data_uri(_themed_illust_path("illust_topright", theme_key)),
        "illust_backpack": _file_to_data_uri(_themed_illust_path("illust_backpack", theme_key)),
        "icon_calendar": icons.ICON_CALENDAR,
        "icon_megaphone": icons.ICON_MEGAPHONE,
        "icon_card": icons.ICON_CARD,
        "icon_star": icons.ICON_STAR,
        "icon_bulb": icons.ICON_BULB,
        "icon_check": icons.ICON_CHECK,
        "icon_heart": icons.ICON_HEART,
        "icon_house": icons.ICON_HOUSE,
        "icon_phone": icons.ICON_PHONE,
        "growth_icons": icons.GROWTH_ICONS,
        "home_icons": icons.HOME_ICONS,
    }

    template = _env.get_template("newsletter_flyer.html")
    return template.render(**ctx)


def render_flyer_png(newsletter, output_path, scale=2):
    from playwright.sync_api import sync_playwright

    html = render_flyer_html(newsletter)
    tmp_html = output_path + ".tmp.html"
    with open(tmp_html, "w", encoding="utf-8") as f:
        f.write(html)

    launch_kwargs = {"args": ["--no-sandbox"]}
    custom_path = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH")
    if custom_path:
        launch_kwargs["executable_path"] = custom_path

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": 1024, "height": 1420}, device_scale_factor=scale)
        page.goto("file://" + os.path.abspath(tmp_html))
        page.wait_for_timeout(150)
        page.screenshot(path=output_path, clip={"x": 0, "y": 0, "width": 1024, "height": 1420})
        browser.close()

    os.remove(tmp_html)
    return output_path
