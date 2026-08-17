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
