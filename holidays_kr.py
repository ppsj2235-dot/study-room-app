"""
대한민국 공휴일 데이터 (달력 자동 생성용).

고정 날짜 공휴일은 매년 동일하고, 설날/추석/부처님오신날처럼 음력 기준인
공휴일은 연도마다 날짜가 바뀝니다. 아래 표는 2025~2028년 기준으로 정리한
값이며, 실제 국가 지정 공휴일과 다르거나 향후 법 개정(대체공휴일 규정 등)으로
바뀔 수 있습니다. 화면(관리자 홈페이지)에서 특정 달의 '추가 휴무일' /
'추가 운영일'을 직접 보정할 수 있으니, 실제와 다르면 그 기능으로 고쳐주세요.
"""

from datetime import date, timedelta

# 매년 날짜가 같은 공휴일 (월, 일, 이름)
FIXED_HOLIDAYS = [
    (1, 1, "신정"),
    (3, 1, "삼일절"),
    (5, 5, "어린이날"),
    (6, 6, "현충일"),
    (8, 15, "광복절"),
    (10, 3, "개천절"),
    (10, 9, "한글날"),
    (12, 25, "성탄절"),
]

# 연도별 음력 기준 공휴일 (설날 연휴 3일, 추석 연휴 3일, 부처님오신날)
LUNAR_HOLIDAYS = {
    2025: {
        (1, 28): "설날 연휴",
        (1, 29): "설날",
        (1, 30): "설날 연휴",
        (5, 5): "부처님오신날",
        (10, 5): "추석 연휴",
        (10, 6): "추석",
        (10, 7): "추석 연휴",
    },
    2026: {
        (2, 16): "설날 연휴",
        (2, 17): "설날",
        (2, 18): "설날 연휴",
        (5, 24): "부처님오신날",
        (9, 24): "추석 연휴",
        (9, 25): "추석",
        (9, 26): "추석 연휴",
    },
    2027: {
        (2, 6): "설날 연휴",
        (2, 7): "설날",
        (2, 8): "설날 연휴",
        (5, 13): "부처님오신날",
        (9, 14): "추석 연휴",
        (9, 15): "추석",
        (9, 16): "추석 연휴",
    },
    2028: {
        (1, 26): "설날 연휴",
        (1, 27): "설날",
        (1, 28): "설날 연휴",
        (5, 2): "부처님오신날",
        (10, 2): "추석 연휴",
        (10, 3): "추석",
        (10, 4): "추석 연휴",
    },
}


def get_holidays_for_year(year):
    """해당 연도의 {date: 이름} 딕셔너리를 반환 (대체공휴일 자동 계산 포함)."""
    holidays = {}
    for month, day, name in FIXED_HOLIDAYS:
        try:
            d = date(year, month, day)
        except ValueError:
            continue
        holidays[d] = name

    for (month, day), name in LUNAR_HOLIDAYS.get(year, {}).items():
        try:
            d = date(year, month, day)
        except ValueError:
            continue
        holidays[d] = name

    # 대체공휴일: 공휴일이 토/일과 겹치면 다음 평일이 대체휴일이 됨 (간단 규칙)
    substitutes = {}
    for d, name in list(holidays.items()):
        if d.weekday() in (5, 6):  # 토(5), 일(6)
            candidate = d + timedelta(days=1)
            while candidate.weekday() in (5, 6) or candidate in holidays:
                candidate += timedelta(days=1)
            substitutes.setdefault(candidate, f"{name} 대체공휴일")

    holidays.update(substitutes)
    return holidays
