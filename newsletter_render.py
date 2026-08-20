# -*- coding: utf-8 -*-
"""알림장(월간 소식지) HTML 렌더링 + 이미지 변환."""

import base64
import os

from jinja2 import Environment, FileSystemLoader

import icons
from newsletter_calendar import build_calendar
from newsletter_themes import DEFAULT_THEME, get_theme_colors

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

    qr_path = newsletter.get("tuition", {}).get("qr_image_path")
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
            "qr_image": _file_to_data_uri(qr_path) if qr_path else "",
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
        page = browser.new_page(viewport={"width": 1024, "height": 1536}, device_scale_factor=scale)
        page.goto("file://" + os.path.abspath(tmp_html))
        page.wait_for_timeout(150)
        page.screenshot(path=output_path, clip={"x": 0, "y": 0, "width": 1024, "height": 1536})
        browser.close()

    os.remove(tmp_html)
    return output_path
