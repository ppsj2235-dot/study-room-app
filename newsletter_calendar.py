# -*- coding: utf-8 -*-
"""달력(10월 운영 일정) 자동 생성 로직."""

import calendar as pycalendar
from datetime import date

from holidays_kr import get_holidays_for_year

WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]
OPERATING_WEEKDAYS = {0, 1, 2, 3}  # 월,화,수,목 (0=월요일)


def build_calendar(year, month, extra_closed_days=None, extra_open_days=None):
    """
    year, month 기준으로 주(월~일) 단위 달력 데이터를 만든다.
    extra_closed_days / extra_open_days: 관리자가 보정하는 '일(day)' 정수 리스트.

    반환: weeks = [[{day, status, label} or None, ...7개...], ...]
          status: 'open'(초록, 운영) | 'closed'(빨강, 휴무)
    """
    extra_closed_days = set(extra_closed_days or [])
    extra_open_days = set(extra_open_days or [])

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
            week.append(None)
        else:
            is_holiday = d in holidays
            weekday = d.weekday()

            if d.day in extra_open_days:
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

    return {
        "weeks": weeks,
        "weekday_labels": WEEKDAY_LABELS,
        "month_days": month_days,
    }
