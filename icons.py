# -*- coding: utf-8 -*-
"""
알림장 디자인에 쓰이는 아주 단순한 라인 아이콘(SVG) 모음.
원본 이미지의 캐릭터 삽화 등은 static/newsletter/ 안의 실제 이미지를 그대로
쓰고, 이 파일은 조그만 안내용 아이콘들만 담당합니다.
"""


def _svg(inner, color="#FBFAF5", size=18, viewbox="0 0 24 24", stroke_width=2):
    return (
        f'<svg width="{size}" height="{size}" viewBox="{viewbox}" fill="none" '
        f'xmlns="http://www.w3.org/2000/svg">{inner}</svg>'
    ).replace("{c}", color).replace("{sw}", str(stroke_width))


ICON_CALENDAR = _svg(
    '<rect x="3" y="5" width="18" height="16" rx="3" stroke="{c}" stroke-width="{sw}"/>'
    '<path d="M3 10h18" stroke="{c}" stroke-width="{sw}"/>'
    '<path d="M8 3v4M16 3v4" stroke="{c}" stroke-width="{sw}" stroke-linecap="round"/>'
)

ICON_MEGAPHONE = _svg(
    '<path d="M3 11v2a2 2 0 002 2h1l2 5h2l-1.5-5H12l7 4V6l-7 4H6a2 2 0 00-2 2z" '
    'stroke="{c}" stroke-width="{sw}" stroke-linejoin="round"/>'
)

ICON_CARD = _svg(
    '<rect x="3" y="6" width="18" height="13" rx="2.5" stroke="{c}" stroke-width="{sw}"/>'
    '<path d="M3 10.5h18" stroke="{c}" stroke-width="{sw}"/>'
    '<path d="M7 15h4" stroke="{c}" stroke-width="{sw}" stroke-linecap="round"/>'
)

ICON_STAR = _svg(
    '<path d="M12 3.5l2.55 5.4 5.95.72-4.4 4.06 1.18 5.87L12 16.9l-5.28 2.65 1.18-5.87-4.4-4.06 '
    '5.95-.72z" fill="{c}"/>',
)

ICON_BULB = _svg(
    '<path d="M9 18h6M10 21h4" stroke="{c}" stroke-width="{sw}" stroke-linecap="round"/>'
    '<path d="M12 3a6.5 6.5 0 00-3.6 11.9c.5.35.9.9 1 1.6h5.2c.1-.7.5-1.25 1-1.6A6.5 6.5 0 0012 3z" '
    'stroke="{c}" stroke-width="{sw}" stroke-linejoin="round"/>'
)

ICON_CHECK = _svg(
    '<path d="M5 13l4.5 4.5L19 8" stroke="{c}" stroke-width="2.6" stroke-linecap="round" '
    'stroke-linejoin="round"/>'
)

ICON_HEART = _svg(
    '<path d="M12 20s-7.5-4.6-9.8-9.3C.6 7 2.4 3.6 6 3.2c2.1-.2 3.9 1 4.9 2.6C11.9 4.2 13.7 3 15.8 3.2c3.6.4 5.4 3.8 3.8 7.5C17.5 15.4 12 20 12 20z" '
    'fill="{c}"/>'
)

ICON_HOUSE = _svg(
    '<path d="M4 11l8-7 8 7" stroke="{c}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M6 9.5V20h12V9.5" stroke="{c}" stroke-width="{sw}" stroke-linejoin="round"/>'
    '<path d="M10 20v-6h4v6" stroke="{c}" stroke-width="{sw}" stroke-linejoin="round"/>'
)

ICON_PHONE = _svg(
    '<path d="M6.5 3.5l3 1.2-1.1 3-1.7-.6a13 13 0 006.2 6.2l-.6-1.7 3-1.1 1.2 3c.3.7-.1 1.5-.8 1.7-6.4 1.8-12-3.8-10.2-10.2.2-.7 1-1.1 1.7-.8z" '
    'stroke="{c}" stroke-width="{sw}" stroke-linejoin="round"/>'
)

# 성장 포인트 아이콘 (초록 톤)
ICON_TARGET = _svg(
    '<circle cx="12" cy="12" r="8" stroke="{c}" stroke-width="{sw}"/>'
    '<circle cx="12" cy="12" r="4.3" stroke="{c}" stroke-width="{sw}"/>'
    '<circle cx="12" cy="12" r="1" fill="{c}"/>',
    color="#527D33",
)
ICON_BARCHART = _svg(
    '<path d="M5 19V13M11 19V9M17 19V5" stroke="{c}" stroke-width="{sw}" stroke-linecap="round"/>',
    color="#527D33",
)
ICON_TROPHY = _svg(
    '<path d="M7 4h10v4a5 5 0 01-10 0V4z" stroke="{c}" stroke-width="{sw}" stroke-linejoin="round"/>'
    '<path d="M7 5H4a3 3 0 003 4M17 5h3a3 3 0 01-3 4" stroke="{c}" stroke-width="{sw}" stroke-linecap="round"/>'
    '<path d="M12 13v3M9 20h6M9.5 20c0-2 1-2.5 2.5-2.5s2.5.5 2.5 2.5" stroke="{c}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>',
    color="#C9971E",
)

# 가정에서 부탁드립니다 아이콘
ICON_BOOK = _svg(
    '<path d="M4 5.5S6 4 12 6c6-2 8-.5 8-.5V18s-2-1.5-8 .5c-6-2-8-.5-8-.5V5.5z" '
    'stroke="{c}" stroke-width="{sw}" stroke-linejoin="round"/>'
    '<path d="M12 6v12.5" stroke="{c}" stroke-width="{sw}"/>',
    color="#3f7a6e",
)
ICON_PENCILCUP = _svg(
    '<rect x="6" y="10" width="12" height="10" rx="1.5" stroke="{c}" stroke-width="{sw}"/>'
    '<path d="M9 10V6l1.5-3 1.5 3v4M14 10V7l1.2-2.2L16.4 7v3" stroke="{c}" stroke-width="{sw}" '
    'stroke-linecap="round" stroke-linejoin="round"/>',
    color="#E08A2E",
)
ICON_PHONE2 = _svg(
    '<path d="M6.5 3.5l3 1.2-1.1 3-1.7-.6a13 13 0 006.2 6.2l-.6-1.7 3-1.1 1.2 3c.3.7-.1 1.5-.8 1.7-6.4 1.8-12-3.8-10.2-10.2.2-.7 1-1.1 1.7-.8z" '
    'stroke="{c}" stroke-width="{sw}" stroke-linejoin="round"/>',
    color="#527D33",
)
ICON_HANDS = _svg(
    '<path d="M12 3v9M8 5.5l4 6.5 4-6.5" stroke="{c}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M5 21c1-4 3-6 7-6s6 2 7 6" stroke="{c}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>',
    color="#C97A4A",
)

GROWTH_ICONS = [ICON_TARGET, ICON_BARCHART, ICON_TROPHY]
HOME_ICONS = [ICON_BOOK, ICON_PENCILCUP, ICON_PHONE2, ICON_HANDS]
