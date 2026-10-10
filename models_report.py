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
"""
import csv
import io
import os
import time
import urllib.error
import urllib.request
from functools import lru_cache

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
    class_totals = [_student_total(s) for s in students]
    class_avg = round(sum(class_totals) / len(class_totals), 1) if class_totals else 0

    units = _unit_order(questions)
    unit_stats = []
    for unit in units:
        q_nums = [q for q, info in questions.items() if info["unit"] == unit]
        unit_max = round(len(q_nums) * point_value, 1)

        student_correct = sum(1 for q in q_nums if target["answers"].get(q))
        student_unit_score = round(student_correct * point_value, 1)

        class_scores = []
        for s in students:
            c = sum(1 for q in q_nums if s["answers"].get(q))
            class_scores.append(c * point_value)
        unit_avg = round(sum(class_scores) / len(class_scores), 1) if class_scores else 0

        unit_stats.append(
            {
                "name": unit,
                "score": student_unit_score,
                "max": unit_max,
                "avg": unit_avg,
                "pct": round(student_unit_score / unit_max * 100, 1) if unit_max else 0,
                "avg_pct": round(unit_avg / unit_max * 100, 1) if unit_max else 0,
            }
        )

    wrong_items = []
    for qnum in sorted(questions.keys()):
        if not target["answers"].get(qnum):
            info = questions[qnum]
            wrong_items.append({"qnum": qnum, **info})

    summary = _build_summary(total_score, class_avg, unit_stats, wrong_items)
    trend_points, trend_caption = _build_trend(grade, student_name, exam["exam_id"])

    return {
        "exam": exam,
        "grade": grade,
        "grade_label": GRADE_LABELS.get(str(grade), f"{grade}학년"),
        "student_name": student_name,
        "total_score": total_score,
        "class_avg": class_avg,
        "diff_vs_avg": round(total_score - class_avg, 1),
        "unit_stats": unit_stats,
        "unit_range": " · ".join(units) if units else "-",
        "wrong_items": wrong_items,
        "correct_count": n_questions - len(wrong_items),
        "total_questions": n_questions,
        "summary": summary,
        "trend_points": trend_points,
        "trend_caption": trend_caption,
    }


def _build_summary(total_score, class_avg, unit_stats, wrong_items):
    parts = []
    if total_score >= class_avg:
        parts.append(
            f"이번 시험에서 {total_score:.0f}점을 받아 응시자 평균({class_avg:.0f}점)보다 높은 성취를 보였습니다."
        )
    else:
        parts.append(
            f"이번 시험에서 {total_score:.0f}점을 받았습니다 (응시자 평균 {class_avg:.0f}점)."
        )

    strong_units = [u for u in unit_stats if u["pct"] >= 90]
    weak_units = [u for u in unit_stats if u["pct"] < u["avg_pct"]]
    if strong_units:
        parts.append("특히 " + ", ".join(u["name"] for u in strong_units) + " 단원에서 우수한 성취를 보였습니다.")
    if weak_units:
        parts.append(", ".join(u["name"] for u in weak_units) + " 단원은 평균보다 다소 낮아 보완이 필요합니다.")

    if wrong_items:
        confusions = [w["confusion"] for w in wrong_items if w.get("confusion")]
        if confusions:
            parts.append("틀린 문항을 살펴보면 " + "; ".join(confusions[:3]) + " 부분에서 혼동이 있었던 것으로 보입니다.")
    else:
        parts.append("전 문항을 정확히 풀어내는 꼼꼼함을 보여주었습니다.")

    return " ".join(parts)


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
