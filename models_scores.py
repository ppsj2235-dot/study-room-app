# -*- coding: utf-8 -*-
"""중간고사 / 기말고사 / 월말고사 점수 관리 (관리자 전용 등록)."""

from db import db_cursor

EXAM_TYPES = ["중간고사", "기말고사", "월말고사"]

# 기본 과목은 수학 하나지만, 방학 때 국어 특강처럼 과목이 늘어날 수 있어
# 목록은 "추천값"일 뿐이고 실제로는 자유 입력(직접 타이핑)도 허용합니다.
SUBJECT_SUGGESTIONS = ["수학", "국어(방학특강)"]


class ExamScore:
    def __init__(self, row):
        self.id = row["id"]
        self.parent_id = row["parent_id"]
        self.exam_type = row["exam_type"]
        self.subject = row["subject"]
        self.score = row["score"]
        self.max_score = row["max_score"]
        self.exam_date = row["exam_date"]
        self.note = row["note"]
        self.created_at = row["created_at"]
        self.updated_at = row["updated_at"]
        # users 테이블과 JOIN 했을 때만 채워짐
        self.student_name = row["student_name"] if "student_name" in row.keys() else None
        self.parent_name = row["parent_name"] if "parent_name" in row.keys() else None

    @property
    def score_display(self):
        # 정수면 소수점 없이, 아니면 그대로 표시
        if float(self.score).is_integer():
            score = int(self.score)
        else:
            score = self.score
        if float(self.max_score).is_integer():
            max_score = int(self.max_score)
        else:
            max_score = self.max_score
        return f"{score} / {max_score}"


_LIST_QUERY = """
    SELECT es.*, u.student_name AS student_name, u.name AS parent_name
    FROM exam_scores es
    JOIN users u ON u.id = es.parent_id
"""


def list_scores(parent_id=None):
    query = _LIST_QUERY
    params = []
    if parent_id:
        query += " WHERE es.parent_id = ?"
        params.append(parent_id)
    query += " ORDER BY es.exam_date DESC, es.created_at DESC"
    with db_cursor() as cur:
        cur.execute(query, params)
        return [ExamScore(row) for row in cur.fetchall()]


def get_score(score_id):
    with db_cursor() as cur:
        cur.execute(_LIST_QUERY + " WHERE es.id = ?", (score_id,))
        row = cur.fetchone()
        return ExamScore(row) if row else None


def create_score(parent_id, exam_type, subject, score, max_score, exam_date, note, created_by):
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO exam_scores
                (parent_id, exam_type, subject, score, max_score, exam_date, note, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (parent_id, exam_type, subject, score, max_score, exam_date, note, created_by),
        )
        return cur.lastrowid


def update_score(score_id, parent_id, exam_type, subject, score, max_score, exam_date, note):
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE exam_scores
            SET parent_id = ?, exam_type = ?, subject = ?, score = ?, max_score = ?,
                exam_date = ?, note = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (parent_id, exam_type, subject, score, max_score, exam_date, note, score_id),
        )


def delete_score(score_id):
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM exam_scores WHERE id = ?", (score_id,))


def _sort_key(row):
    # exam_date가 없으면 등록 순서(created_at)로 대체 정렬
    return (row.exam_date or "", row.created_at or "")


def build_subject_trends(score_rows, flag_below_pct=70):
    """학부모 화면용: 과목별로 묶어서 시간순 추이(그래프용 좌표)를 만들어줍니다.

    과목이 '수학' 하나뿐이어도, 방학 특강처럼 과목이 늘어나도 그대로 동작합니다.
    """
    groups = {}
    order = []
    for row in score_rows:
        if row.subject not in groups:
            groups[row.subject] = []
            order.append(row.subject)
        groups[row.subject].append(row)

    trends = []
    for subject in order:
        rows_sorted = sorted(groups[subject], key=_sort_key)
        n = len(rows_sorted)
        points = []
        for i, row in enumerate(rows_sorted):
            pct = (row.score / row.max_score * 100) if row.max_score else 0
            x = 10 if n <= 1 else round(10 + (280 * i / (n - 1)), 1)
            y = round(58 - (pct / 100 * 48), 1)
            points.append(
                {
                    "x": x,
                    "y": y,
                    "pct": round(pct, 1),
                    "score_display": row.score_display,
                    "exam_type": row.exam_type,
                    "exam_date": row.exam_date,
                }
            )

        latest_row = rows_sorted[-1]
        latest_pct = points[-1]["pct"]
        prev_pct = points[-2]["pct"] if n >= 2 else None
        delta = None if prev_pct is None else round(latest_pct - prev_pct, 1)
        flagged = latest_pct < flag_below_pct or (delta is not None and delta < 0)

        trends.append(
            {
                "subject": subject,
                "count": n,
                "points": points,
                "polyline": " ".join(f'{p["x"]},{p["y"]}' for p in points),
                "latest": latest_row,
                "latest_pct": latest_pct,
                "delta": delta,
                "flagged": flagged,
            }
        )
    return trends
