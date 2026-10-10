# -*- coding: utf-8 -*-
"""성적표(학습 평가표) HTML 렌더링 + 이미지 변환.

newsletter_render.py와 완전히 동일한 방식(Jinja2로 HTML을 만들고, Playwright로
그 HTML을 그대로 캡처해서 PNG로 저장)을 그대로 따릅니다.
"""
import os

from jinja2 import Environment, FileSystemLoader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, "templates")))


def render_report_html(report, academy_name):
    template = _env.get_template("report_card.html")
    return template.render(report=report, academy_name=academy_name)


def render_report_png(report, academy_name, output_path, scale=2):
    from playwright.sync_api import sync_playwright

    html = render_report_html(report, academy_name)
    tmp_html = output_path + ".tmp.html"
    with open(tmp_html, "w", encoding="utf-8") as f:
        f.write(html)

    launch_kwargs = {"args": ["--no-sandbox"]}
    custom_path = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH")
    if custom_path:
        launch_kwargs["executable_path"] = custom_path

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        # 단원 개수·오답 개수에 따라 리포트 세로 길이가 조금씩 달라질 수 있어서,
        # 알림장처럼 높이를 고정해서 자르지 않고 full_page로 실제 길이만큼 캡처합니다.
        page = browser.new_page(viewport={"width": 800, "height": 1200}, device_scale_factor=scale)
        page.goto("file://" + os.path.abspath(tmp_html))
        page.wait_for_timeout(150)
        page.screenshot(path=output_path, full_page=True)
        browser.close()

    os.remove(tmp_html)
    return output_path
