# -*- coding: utf-8 -*-
"""달력(10월 운영 일정) 자동 생성 로직."""

import calendar as pycalendar
from datetime import date

from holidays_kr import get_holidays_for_year

WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]
OPERATING_WEEKDAYS = {0, 1, 2, 3}  # 월,화,수,목 (0=월요일)


def parse_day_ranges(text):
    """'28~31', '5, 12-14' 같은 문자열을 [28,29,30,31] / [5,12,13,14] 정수 리스트로."""
    if not text:
        return []
    out = []
    for part in text.replace("\n", ",").split(","):
        part = part.strip().replace("~", "-").replace("–", "-")
        if not part:
            continue
        if part.isdigit():
            out.append(int(part))
            continue
        pieces = [x.strip() for x in part.split("-")]
        if len(pieces) == 2 and pieces[0].isdigit() and pieces[1].isdigit():
            start, end = int(pieces[0]), int(pieces[1])
            if start <= end <= 31:
                out.extend(range(start, end + 1))
    return sorted(set(out))


def _format_vacation_range(month, days):
    """[28,29,30,31] -> '12/28~12/31', [5,12] -> '12/5, 12/12'"""
    days = sorted(set(days))
    groups = []
    for d in days:
        if groups and d == groups[-1][1] + 1:
            groups[-1][1] = d
        else:
            groups.append([d, d])
    parts = []
    for a, b in groups:
        parts.append(f"{month}/{a}" if a == b else f"{month}/{a}~{month}/{b}")
    return ", ".join(parts)


def build_calendar(year, month, extra_closed_days=None, extra_open_days=None, vacation_days=None):
    """
    year, month 기준으로 주(월~일) 단위 달력 데이터를 만든다.
    extra_closed_days / extra_open_days: 관리자가 보정하는 '일(day)' 정수 리스트.

    반환: weeks = [[{day, status, label} or None, ...7개...], ...]
          status: 'open'(초록, 운영) | 'closed'(빨강, 휴무) | 'vacation'(주황, 방학)
    """
    extra_closed_days = set(extra_closed_days or [])
    extra_open_days = set(extra_open_days or [])
    vacation_days = set(vacation_days or [])

    holidays = get_holidays_for_year(year)
    if month == 12:
        holidays.update(get_holidays_for_year(year + 1))
    if month == 1:
        holidays.update(get_holidays_for_year(year - 1))

    month_days = pycalendar.monthrange(year, month)[1]
    weeks = []
    cal = pycalendar.Calendar(firstweekday=0)  # 월요일 시작

    week = []
    for d in cal.itermonthdates(year, month):
        in_month = d.month == month
        if not in_month:
            # 이전 달의 마지막 날이 월요일이면(이전 달 알림장에서 "다음달 수업으로 이어지는 날"로 표시되는 날)
            # 이번 달 첫 주 월요일 칸에 운영일로 함께 넣는다. 예) 11/30(월) -> 12월 달력 첫째 주 월요일
            first_day = date(year, month, 1)
            if d.weekday() == 0 and (first_day - d).days == 1:
                week.append(
                    {
                        "day": d.day,
                        "status": "closed" if d in holidays else "open",
                        "holiday_name": holidays.get(d),
                        "is_leading": True,
                        "from_month": d.month,
                    }
                )
            else:
                week.append(None)
        else:
            is_holiday = d in holidays
            weekday = d.weekday()

            if d.day in vacation_days:
                status = "vacation"
            elif d.day in extra_open_days:
                status = "open"
            elif d.day in extra_closed_days:
                status = "closed"
            elif is_holiday:
                status = "closed"
            elif weekday in OPERATING_WEEKDAYS:
                status = "open"
            else:
                status = "closed"

            week.append(
                {
                    "day": d.day,
                    "status": status,
                    "holiday_name": holidays.get(d),
                }
            )
        if len(week) == 7:
            weeks.append(week)
            week = []

    # 앞뒤로 완전히 빈 주는 제거하지 않고 그대로 둔다 (레이아웃 일관성)
    # 단, 모든 값이 None인 주만 있다면 제거
    weeks = [w for w in weeks if any(cell is not None for cell in w)]

    # 그 달의 마지막 날이 혼자 새 주로 넘어가 있으면(같은 주에 다른 날짜가 없으면)
    # 알림장에서 "다음달 수업으로 이어지는 날"로 다르게 표시할 수 있도록 표시해둔다.
    if weeks:
        last_week = weeks[-1]
        non_empty = [cell for cell in last_week if cell is not None]
        if len(non_empty) == 1 and non_empty[0]["day"] == month_days:
            non_empty[0]["is_trailing"] = True

    return {
        "weeks": weeks,
        "weekday_labels": WEEKDAY_LABELS,
        "month_days": month_days,
        "vacation_range": _format_vacation_range(
            month, [d for d in vacation_days if 1 <= d <= month_days]
        ),
    }
