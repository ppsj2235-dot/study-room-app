# -*- coding: utf-8 -*-
"""알림장 색상 테마.

디자인(레이아웃/구성)은 고정이지만, 관리자가 상황/계절에 맞춰 색감만 바꿀 수 있도록
테마별 색상 값을 여기 한 곳에 모아둡니다. 새 테마를 추가하려면 이 딕셔너리에
항목만 추가하면 관리자 화면 선택지와 알림장 렌더링에 자동으로 반영됩니다.

각 값의 역할:
- dark: 리본/카드 헤더 바/아이콘 배지/푸터 등 진한 브랜드 색
- positive: 운영일(달력 초록 계열) + 부제목 밑줄 텍스트 + 성장 포인트 아이콘 테두리
- positive_light: 부제목 밑줄 바 색 (positive의 연한 톤)
- negative: 휴무일(달력) + 학습TIP 헤더 + 주말 라벨 + 학습TIP 아이콘 테두리
- bg: 페이지 배경 + 진한 배경 위 밝은 글자색
- card_bg: 카드 내부 배경 (bg보다 살짝 다른 톤)
- border: 카드 테두리
- frame_border: 페이지 맨 바깥 테두리
"""

DEFAULT_THEME = "green"

THEMES = {
    "green": {
        "label": "그린 (기본)",
        "dark": "#04482B",
        "positive": "#527D33",
        "positive_light": "#C7D2A4",
        "negative": "#E8433A",
        "bg": "#FBFAF5",
        "card_bg": "#FCFAF6",
        "border": "#E7E3D6",
        "frame_border": "#E3E0D4",
    },
    "autumn": {
        "label": "가을 (브라운/오렌지)",
        "dark": "#6B3A1E",
        "positive": "#7C7233",
        "positive_light": "#D9CE9C",
        "negative": "#C1442C",
        "bg": "#FBF3E7",
        "card_bg": "#FCF6EC",
        "border": "#EADFCB",
        "frame_border": "#E5D8BE",
    },
    "winter": {
        "label": "겨울 (네이비/블루)",
        "dark": "#17324F",
        "positive": "#3E7A8C",
        "positive_light": "#C4DCE3",
        "negative": "#C24545",
        "bg": "#F2F6F8",
        "card_bg": "#F7FAFB",
        "border": "#DCE6EB",
        "frame_border": "#D5E1E7",
    },
    "spring": {
        "label": "봄 (핑크/그린)",
        "dark": "#7A3B54",
        "positive": "#5E8C61",
        "positive_light": "#CFE3D0",
        "negative": "#E0607A",
        "bg": "#FDF3F6",
        "card_bg": "#FEF8FA",
        "border": "#F2DEE6",
        "frame_border": "#EED4DE",
    },
    "summer": {
        "label": "여름 (틸/코랄)",
        "dark": "#0B5E63",
        "positive": "#2E8B57",
        "positive_light": "#BFE3CD",
        "negative": "#E4572E",
        "bg": "#F2FBF9",
        "card_bg": "#F7FDFB",
        "border": "#D7EDE6",
        "frame_border": "#CDE7DE",
    },
    "oatmeal_terracotta": {
        "label": "오트밀 + 테라코타",
        "dark": "#806052",
        "positive": "#C97D60",
        "positive_light": "#E7BFA9",
        "negative": "#B24A34",
        "bg": "#FAF8F7",
        "card_bg": "#FCFAFA",
        "border": "#EBDFD9",
        "frame_border": "#E8DBD4",
    },
    "butter_olive": {
        "label": "버터 + 올리브",
        "dark": "#6E7050",
        "positive": "#D6B65C",
        "positive_light": "#A8A77A",
        "negative": "#B2543F",
        "bg": "#F9F9F8",
        "card_bg": "#FBFBFA",
        "border": "#E5E5DE",
        "frame_border": "#E1E1DA",
    },
    "apricot_brown": {
        "label": "살구 + 브라운",
        "dark": "#765348",
        "positive": "#E8A47C",
        "positive_light": "#F3D2B8",
        "negative": "#C2503A",
        "bg": "#FBF8F7",
        "card_bg": "#FCFBFA",
        "border": "#EDE0D6",
        "frame_border": "#EADCD2",
    },
    "sage_beige": {
        "label": "세이지 + 베이지",
        "dark": "#66715E",
        "positive": "#91A58B",
        "positive_light": "#D6C8AE",
        "negative": "#BF5B45",
        "bg": "#FAF9F8",
        "card_bg": "#FBFBFA",
        "border": "#E7E3DC",
        "frame_border": "#E4E0D8",
    },
    "cream_mustard": {
        "label": "크림 + 머스타드",
        "dark": "#765C36",
        "positive": "#D6A84B",
        "positive_light": "#E9CF91",
        "negative": "#BD5A34",
        "bg": "#FAF9F7",
        "card_bg": "#FCFBFA",
        "border": "#ECE6D7",
        "frame_border": "#E9E3D2",
    },
    "coral_deepgreen": {
        "label": "코랄 + 딥그린",
        "dark": "#526B5B",
        "positive": "#D98670",
        "positive_light": "#EBC2AE",
        "negative": "#B23F35",
        "bg": "#FAF8F7",
        "card_bg": "#FCFAFA",
        "border": "#EBDED8",
        "frame_border": "#E8DAD3",
    },
    "gimpopay_x": {
        # 코랄 + 딥그린과 색감은 동일하고, 김포페이 QR 없이 쓰는 달을 구분하기 위한 이름만 다른 테마
        "label": "김포페이X",
        "dark": "#526B5B",
        "positive": "#D98670",
        "positive_light": "#EBC2AE",
        "negative": "#B23F35",
        "bg": "#FAF8F7",
        "card_bg": "#FCFAFA",
        "border": "#EBDED8",
        "frame_border": "#E8DAD3",
    },
}


def get_theme_colors(theme_key):
    return THEMES.get(theme_key, THEMES[DEFAULT_THEME])


def theme_choices():
    """관리자 화면 선택지용: [(key, label, dark, positive, negative), ...]"""
    return [
        (key, t["label"], t["dark"], t["positive"], t["negative"])
        for key, t in THEMES.items()
    ]
