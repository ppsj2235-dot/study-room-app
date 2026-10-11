# -*- coding: utf-8 -*-
"""구글시트 기반 성적표(학습 평가표) 데이터 수집 + 집계.

모든 원본 데이터(문항 정보, 학생별 채점)는 구글 스프레드시트에서
"웹에 게시(CSV)"로 공개한 링크를 통해 읽어옵니다. 서비스 계정이나 API 키 같은
별도 인증이 전혀 필요 없고, 관리자가 구글시트에서 체크박스로 채점만 해두면
홈페이지의 성적표 다운로드 화면에 그대로 반영됩니다.

[중요] 시험은 1년에 4번(1학기 중간/기말, 2학기 중간/기말) 누적됩니다. 새 시험을
치를 때마다:
  1) 구글시트에 그 학년들의 새 채점 탭(+필요하면 새 문항정보 행)을 추가하고
  2) 각 탭을 "웹에 게시 > CSV"로 게시해서 gid를 확인한 뒤
  3) 아래 EXAMS 리스트에 항목을 하나 추가하면
"회차별 점수 추이" 그래프가 자동으로 그 시험을 포함해서 다시 그려집니다.
이 로직을 바꾸지 않고 유지해야, 나중에 1학기/2학기 중간/기말 4회를 연결한
그래프를 그대로 볼 수 있습니다.

[총평] 성적표의 "04 · 총평 및 보완 포인트"는 기본적으로 학생 본인의 결과(오답 단원,
혼동 포인트)만 보고 자동으로 문장을 만들어 보여줍니다(다른 학생과의 "평균 비교"는
쓰지 않습니다 - 학생 수가 적은 학년이 많아 비교 자체가 의미가 없기 때문입니다).
관리자가 문구를 직접 고치고 싶으면 홈페이지 성적표 관리 화면에서 "총평 수정"으로
들어가 고쳐 쓸 수 있고, 그 내용은 DB(report_comments 테이블)에 저장되어 자동 생성
문구 대신 표시됩니다. 수정 화면에서 비워서 저장하면 다시 자동 생성 문구로
돌아갑니다. (예전에는 구글시트 "총평" 열에 적는 방식이었지만, 수정 경로를 홈페이지
하나로 통일하면서 구글시트 쪽은 더 이상 읽지 않습니다)
"""
import csv
import io
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from functools import lru_cache

from db import db_cursor

# 구글시트 "웹에 게시" 링크에 공통으로 들어가는 토큰. 민감한 로그인 정보는
# 아니지만(링크를 아는 사람만 열람 가능한 수준), 공개 저장소 코드에 그대로
# 적어두지 않기 위해 다른 설정값(DATABASE_URL, SECRET_KEY 등)과 동일하게
# Render 환경변수로 등록해서 씁니다.
GSHEET_PUB_TOKEN = os.environ.get("GSHEET_PUB_TOKEN", "")

GRADES = ["3", "4", "5", "6"]
GRADE_LABELS = {"3": "3학년", "4": "4학년", "5": "5학년", "6": "6학년"}

# 시험 회차 목록 (새 시험을 추가할 때는 이 리스트 맨 뒤에 항목만 추가하면 됩니다)
EXAMS = [
    {
        "exam_id": "2026-2-mid",
        "label": "2학기 중간고사",
        "year": 2026,
        "semester": 2,
        "exam_type": "중간고사",
        "round_label": "1회",
        "exam_date": "2026-10-08",  # 실제 응시일로 자유롭게 수정하세요
        "questions_gid": "0",
        "grade_gids": {
            "3": "1414399468",
            "4": "630224774",
            "5": "1447321834",
            "6": "392209813",
        },
    },
]


def _csv_url(gid):
    # 캐시 무력화용 타임스탬프를 매번 붙입니다. 구글이 "웹에 게시" CSV를
    # 몇 분간 캐싱해서 내보내는 경우가 있어서, URL을 매 요청마다 조금씩
    # 다르게 만들어야 방금 구글시트에서 수정한 내용이 바로 반영됩니다.
    cache_bust = int(time.time() * 1000)
    return (
        f"https://docs.google.com/spreadsheets/d/e/{GSHEET_PUB_TOKEN}"
        f"/pub?gid={gid}&single=true&output=csv&_cb={cache_bust}"
    )


def _fetch_csv(gid, timeout=10):
    if not GSHEET_PUB_TOKEN:
        return []
    url = _csv_url(gid)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8-sig")
    except (urllib.error.URLError, TimeoutError):
        return []
    return list(csv.DictReader(io.StringIO(raw)))


def _to_bool(v):
    return str(v).strip().upper() == "TRUE"


def get_exam(exam_id):
    for e in EXAMS:
        if e["exam_id"] == exam_id:
            return e
    return None


def latest_exam():
    return EXAMS[-1] if EXAMS else None


@lru_cache(maxsize=64)
def _load_questions_cached(exam_id, questions_gid):
    rows = _fetch_csv(questions_gid)
    by_grade = {}
    for row in rows:
        grade = str(row.get("학년", "")).strip()
        try:
            qnum = int(str(row.get("문항", "")).strip())
        except ValueError:
            continue
        by_grade.setdefault(grade, {})[qnum] = {
            "unit": (row.get("단원") or "").strip(),
            "content": (row.get("평가내용") or "").strip(),
            "difficulty": (row.get("난이도") or "").strip(),
            "domain": (row.get("행동영역") or "").strip(),
            "confusion": (row.get("혼동포인트") or "").strip(),
        }
    return by_grade


def load_questions(exam, grade):
    by_grade = _load_questions_cached(exam["exam_id"], exam["questions_gid"])
    return by_grade.get(str(grade), {})


def clear_cache():
    """문항정보 캐시를 비웁니다. 관리자가 "최신 자료 새로고침" 버튼을 누르면
    호출되어, 구글시트의 문항정보 탭을 수정한 내용도 즉시 반영되게 합니다.
    (채점 결과/총점은 애초에 캐시하지 않고 매번 새로 읽어오므로 영향 없음)
    """
    _load_questions_cached.cache_clear()


def load_grade_sheet(exam, grade):
    """해당 학년 채점 시트의 모든 학생 행을 반환합니다.

    (시트가 아직 "준비 중"이라 문항 체크박스가 없는 경우 - 예: 아직 시험지가
    없는 6학년 - answers는 빈 딕셔너리, total은 None으로 채워집니다.)
    """
    gid = exam["grade_gids"].get(str(grade))
    if not gid:
        return []
    rows = _fetch_csv(gid)
    students = []
    for row in rows:
        name = (row.get("이름") or "").strip()
        if not name:
            continue
        answers = {}
        for key, val in row.items():
            if key and key.startswith("문항"):
                try:
                    qnum = int(key.replace("문항", "").strip())
                except ValueError:
                    continue
                answers[qnum] = _to_bool(val)
        total_raw = (row.get("총점") or "").strip()
        try:
            total = float(total_raw)
        except ValueError:
            total = None
        students.append({"name": name, "answers": answers, "total": total})
    return students


def list_students(exam, grade):
    return [s["name"] for s in load_grade_sheet(exam, grade)]


def _unit_order(questions):
    """문항 번호 순서를 기준으로 단원이 처음 등장하는 순서를 유지합니다."""
    seen = []
    for qnum in sorted(questions.keys()):
        u = questions[qnum]["unit"]
        if u and u not in seen:
            seen.append(u)
    return seen


def _has_batchim(text):
    """문자열 마지막 글자에 받침이 있는지 (이/가 같은 조사를 고르기 위함)."""
    if not text:
        return False
    code = ord(text[-1]) - 0xAC00
    if code < 0 or code > 11171:
        return False
    return (code % 28) != 0


def _complete_sentence(text):
    """구글시트 '혼동포인트' 칸에 "못함"처럼 짧게 줄여 적은 메모를, 자동 생성
    총평 문장 안에 그대로 끼워 넣으면 "못함" 패턴처럼 말이 어색하게 잘린다.
    간추리지 않고 정중하게 끝맺는 완전한 문장(예: "못함" -> "못하였습니다")으로
    바꿔서 돌려준다."""
    text = (text or "").strip()
    if not text:
        return text
    if text.endswith(("습니다", "어요", "아요", "네요", "군요", "했어요")):
        return text
    if text.endswith("함"):
        return text[:-1] + "하였습니다"
    particle = "이" if _has_batchim(text) else "가"
    return f"{text}{particle} 있었습니다"


def _auto_comment(total_score, unit_stats, wrong_items, correct_count, n_questions):
    """학생 본인의 이번 시험 결과(오답 단원 · 혼동 포인트)만 보고 "총평" 문구를
    자동으로 만듭니다 (다른 학생/반 평균과 비교하지 않습니다 - 위 [총평] 설명
    참고). "집에서 연습하라"는 안내가 아니라, 공부방에서 앞으로 어떻게 보충
    지도할지를 알려주는 톤으로 씁니다. 관리자가 홈페이지에서 직접 고쳐 쓰면
    이 자동 문구 대신 그 내용이 쓰입니다.
    """
    if not wrong_items:
        return (
            f"이번 시험에서 {n_questions}문항을 모두 맞혔어요! "
            "지금처럼 꾸준히 실력을 유지해주시면 좋겠습니다."
        )

    weak_units = sorted((u for u in unit_stats if u["pct"] < 100), key=lambda u: u["pct"])
    weak_names = " · ".join(u["name"] for u in weak_units[:2]) if weak_units else ""

    confusions = [w["confusion"] for w in wrong_items if w.get("confusion")]
    top_confusion = Counter(confusions).most_common(1)[0][0] if confusions else ""

    if weak_names and top_confusion:
        confusion_full = _complete_sentence(top_confusion)
        plan = (
            f"'{weak_names}' 단원에서 {confusion_full}. "
            "다음 보충 수업에서 이 부분을 집중적으로 다뤄보겠습니다."
        )
    elif weak_names:
        plan = f"'{weak_names}' 단원 위주로 다음 보충 수업에서 복습을 진행하겠습니다."
    else:
        plan = "틀린 문항들을 다음 보충 수업에서 다시 짚어보겠습니다."

    return f"총 {n_questions}문항 중 {correct_count}문항을 맞혔습니다 ({total_score:.0f}점). {plan}"


def get_comment_override(exam_id, grade, student_name):
    """관리자가 홈페이지에서 직접 고쳐 쓴 총평이 있으면 반환하고, 없으면 None."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT comment FROM report_comments WHERE exam_id = ? AND grade = ? AND student_name = ?",
            (exam_id, str(grade), student_name),
        )
        row = cur.fetchone()
        return row["comment"] if row else None


def set_comment_override(exam_id, grade, student_name, comment, updated_by=None):
    """관리자가 홈페이지에서 총평을 저장합니다. 빈 문자열로 저장하면 override를
    지워서 다시 자동 생성 문구로 돌아갑니다."""
    comment = (comment or "").strip()
    with db_cursor(commit=True) as cur:
        if not comment:
            cur.execute(
                "DELETE FROM report_comments WHERE exam_id = ? AND grade = ? AND student_name = ?",
                (exam_id, str(grade), student_name),
            )
            return
        cur.execute(
            """
            INSERT INTO report_comments (exam_id, grade, student_name, comment, updated_by, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(exam_id, grade, student_name)
            DO UPDATE SET comment = excluded.comment, updated_by = excluded.updated_by, updated_at = CURRENT_TIMESTAMP
            """,
            (exam_id, str(grade), student_name, comment, updated_by),
        )


def build_report(grade, student_name, exam_id=None):
    """한 학생의 성적표에 필요한 모든 집계 데이터를 반환합니다.

    해당 학년에 아직 등록된 시험 자료(문항정보/채점)가 없으면 None을 반환합니다.
    """
    exam = get_exam(exam_id) if exam_id else latest_exam()
    if not exam:
        return None

    questions = load_questions(exam, grade)
    students = load_grade_sheet(exam, grade)
    if not questions or not students:
        return None

    target = next((s for s in students if s["name"] == student_name), None)
    if not target:
        return None

    n_questions = len(questions)
    point_value = 100 / n_questions if n_questions else 0

    def _student_total(s):
        if s["total"] is not None:
            return s["total"]
        return round(sum(1 for v in s["answers"].values() if v) * point_value, 1)

    total_score = _student_total(target)

    units = _unit_order(questions)
    unit_stats = []
    for unit in units:
        q_nums = [q for q, info in questions.items() if info["unit"] == unit]
        unit_max = round(len(q_nums) * point_value, 1)

        student_correct = sum(1 for q in q_nums if target["answers"].get(q))
        student_unit_score = round(student_correct * point_value, 1)

        unit_stats.append(
            {
                "name": unit,
                "score": student_unit_score,
                "max": unit_max,
                "pct": round(student_unit_score / unit_max * 100, 1) if unit_max else 0,
            }
        )

    wrong_items = []
    for qnum in sorted(questions.keys()):
        if not target["answers"].get(qnum):
            info = questions[qnum]
            wrong_items.append({"qnum": qnum, **info})

    correct_count = n_questions - len(wrong_items)

    # "총평"은 기본적으로 학생 본인 결과 기준으로 자동 생성됩니다. 관리자가
    # 홈페이지에서 직접 고쳐 쓴 내용(DB)이 있으면 그 내용이 자동 생성 문구
    # 대신 쓰입니다 - 위 [총평] 설명 참고.
    override = get_comment_override(exam["exam_id"], grade, student_name)
    auto_summary = _auto_comment(total_score, unit_stats, wrong_items, correct_count, n_questions)
    summary = override if override else auto_summary
    trend_points, trend_caption = _build_trend(grade, student_name, exam["exam_id"])

    return {
        "exam": exam,
        "grade": grade,
        "grade_label": GRADE_LABELS.get(str(grade), f"{grade}학년"),
        "student_name": student_name,
        "total_score": total_score,
        "unit_stats": unit_stats,
        "unit_range": " · ".join(units) if units else "-",
        "wrong_items": wrong_items,
        "correct_count": correct_count,
        "total_questions": n_questions,
        "summary": summary,
        "auto_summary": auto_summary,
        "summary_is_manual": bool(override),
        "trend_points": trend_points,
        "trend_caption": trend_caption,
    }


def _build_trend(grade, student_name, current_exam_id):
    raw_points = []
    for exam in EXAMS:
        students = load_grade_sheet(exam, grade)
        s = next((x for x in students if x["name"] == student_name), None)
        if not s:
            continue
        questions = load_questions(exam, grade)
        n_questions = len(questions) or 20
        point_value = 100 / n_questions
        total = s["total"]
        if total is None:
            total = sum(1 for v in s["answers"].values() if v) * point_value
        raw_points.append(
            {
                "exam_id": exam["exam_id"],
                "label": exam.get("round_label") or exam["label"],
                "exam_date": exam.get("exam_date"),
                "score": round(total, 1),
            }
        )

    n = len(raw_points)
    points = []
    for i, p in enumerate(raw_points):
        x = 80.0 if n <= 1 else round(80 + (460 * i / (n - 1)), 1)
        y = round(150 - (p["score"] / 100 * 130), 1)
        p = dict(p, x=x, y=y, svg_point=f"{x},{y}")
        points.append(p)

    if n == 0:
        caption = "아직 시험 데이터가 없습니다."
    elif n == 1:
        caption = "첫 번째 시험 결과예요. 앞으로 시험을 치를 때마다 이 그래프에 점수 변화가 자동으로 쌓여요."
    else:
        scores = [p["score"] for p in points]
        seq = " → ".join(f"{s:.0f}" for s in scores)
        if scores[-1] > scores[0]:
            trend_word = "꾸준히 점수가 오르고 있어요"
        elif scores[-1] < scores[0]:
            trend_word = "최근 점수가 다소 낮아졌어요. 조금 더 신경쓰면 좋겠어요"
        else:
            trend_word = "비슷한 점수대를 꾸준히 유지하고 있어요"
        caption = f"최근 {n}회 시험에서 {trend_word} ({seq})."

    return points, caption
