import os
import secrets
import tempfile
from datetime import date
from functools import wraps

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

import models
import models_newsletter as nl
import models_scores as scores
from content_bank import suggest_director_message, suggest_quote
from db import init_db
from newsletter_render import render_flyer_html, render_flyer_png

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

# 세션 쿠키 보안 옵션 (운영 환경에서 HTTPS 사용 시 SESSION_COOKIE_SECURE=1 로 설정)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"

ACADEMY_NAME = os.environ.get("ACADEMY_NAME", "우리 공부방")


# ---------------------------------------------------------------------------
# 초기화: DB 테이블 생성 + 최초 관리자 계정 자동 생성
# ---------------------------------------------------------------------------
def bootstrap():
    init_db()
    admin_username = os.environ.get("ADMIN_USERNAME")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if admin_username and admin_password:
        if not models.username_exists(admin_username):
            models.create_user(
                username=admin_username,
                password=admin_password,
                role="admin",
                name=os.environ.get("ADMIN_NAME", "관리자"),
            )
            print(f"[bootstrap] 초기 관리자 계정 '{admin_username}' 생성됨")


bootstrap()


# ---------------------------------------------------------------------------
# 공통 유틸: 로그인/권한 체크, CSRF 토큰
# ---------------------------------------------------------------------------
@app.before_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = models.get_user_by_id(user_id) if user_id else None


@app.context_processor
def inject_globals():
    return {
        "academy_name": ACADEMY_NAME,
        "current_user": g.get("user"),
        "csrf_token": get_csrf_token,
    }


def get_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def check_csrf():
    token = request.form.get("csrf_token")
    if not token or token != session.get("csrf_token"):
        abort(400, description="잘못된 요청입니다. 새로고침 후 다시 시도해주세요.")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login", next=request.path))
        if not g.user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def parent_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login", next=request.path))
        if g.user.is_admin:
            return redirect(url_for("admin_dashboard"))
        return view(*args, **kwargs)

    return wrapped


# ---------------------------------------------------------------------------
# 라우트
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    if g.user is None:
        return redirect(url_for("login"))
    if g.user.is_admin:
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("parent_dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("index"))

    if request.method == "POST":
        check_csrf()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = models.get_user_by_username(username)
        if user is None or not models.verify_password(user, password):
            flash("아이디 또는 비밀번호가 올바르지 않습니다.", "error")
            return render_template("login.html"), 401

        session.clear()
        session["user_id"] = user.id
        flash(f"{user.name}님, 환영합니다.", "success")

        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("로그아웃 되었습니다.", "success")
    return redirect(url_for("login"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    parents = models.list_parents()
    return render_template("admin_dashboard.html", parents=parents)


@app.route("/admin/parents", methods=["POST"])
@admin_required
def create_parent():
    check_csrf()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    name = request.form.get("name", "").strip()
    student_name = request.form.get("student_name", "").strip()

    errors = []
    if not username:
        errors.append("아이디를 입력해주세요.")
    elif models.username_exists(username):
        errors.append("이미 사용 중인 아이디입니다.")
    if not password or len(password) < 4:
        errors.append("비밀번호는 4자 이상 입력해주세요.")
    if not name:
        errors.append("학부모 이름을 입력해주세요.")

    if errors:
        for e in errors:
            flash(e, "error")
        return redirect(url_for("admin_dashboard"))

    models.create_user(
        username=username,
        password=password,
        role="parent",
        name=name,
        student_name=student_name or None,
    )
    flash(f"학부모 계정 '{username}' 이(가) 생성되었습니다.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/parents/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_parent(user_id):
    check_csrf()
    models.delete_user(user_id)
    flash("계정이 삭제되었습니다.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/parents/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def reset_parent_password(user_id):
    check_csrf()
    new_password = request.form.get("new_password", "")
    if not new_password or len(new_password) < 4:
        flash("비밀번호는 4자 이상 입력해주세요.", "error")
        return redirect(url_for("admin_dashboard"))
    models.reset_password(user_id, new_password)
    flash("비밀번호가 재설정되었습니다.", "success")
    return redirect(url_for("admin_dashboard"))


UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "newsletter", "uploads")


def _form_list(prefix, count):
    return [request.form.get(f"{prefix}_{i}", "").strip() for i in range(1, count + 1)]


def _parse_newsletter_form(form, existing_qr_path=None):
    notices = [n for n in _form_list("notice", 5) if n]
    if not notices:
        notices = [""]

    growth_titles = _form_list("growth_title", 3)
    growth_descs = _form_list("growth_desc", 3)
    growth_items = [{"title": t, "desc": d} for t, d in zip(growth_titles, growth_descs)]

    tip_items = [t for t in _form_list("tip", 3)]

    home_titles = _form_list("home_title", 4)
    home_descs = _form_list("home_desc", 4)
    home_items = [{"title": t, "desc": d} for t, d in zip(home_titles, home_descs)]

    data = {
        "academy_name": form.get("academy_name", "").strip() or ACADEMY_NAME,
        "tagline": form.get("tagline", "").strip(),
        "notices": notices,
        "tuition": {
            "period": form.get("tuition_period", "").strip(),
            "account": form.get("tuition_account", "").strip(),
            "note": form.get("tuition_note", "").strip(),
            "qr_label": form.get("tuition_qr_label", "").strip() or "QR코드",
            "qr_image_path": existing_qr_path,
        },
        "growth_items": growth_items,
        "tip_items": tip_items,
        "home_items": home_items,
        "director_message": form.get("director_message", "").strip(),
        "quote_text": form.get("quote_text", "").strip(),
        "quote_author": form.get("quote_author", "").strip(),
        "contact": {
            "phone": form.get("contact_phone", "").strip(),
            "address": form.get("contact_address", "").strip(),
            "note": form.get("contact_note", "").strip(),
        },
        "extra_closed_days": nl.parse_day_list(form.get("extra_closed_days", "")),
        "extra_open_days": nl.parse_day_list(form.get("extra_open_days", "")),
    }
    return data


@app.route("/admin/newsletters")
@admin_required
def newsletter_list():
    newsletters = nl.list_newsletters()
    latest = newsletters[0] if newsletters else None
    today = date.today()
    if latest:
        default_year, default_month = latest["year"], latest["month"]
        default_month += 1
        if default_month > 12:
            default_month = 1
            default_year += 1
    else:
        default_year, default_month = today.year, today.month

    year_options = list(range(today.year - 1, today.year + 3))
    return render_template(
        "admin_newsletter_list.html",
        newsletters=newsletters,
        default_year=default_year,
        default_month=default_month,
        year_options=year_options,
    )


@app.route("/admin/newsletters/new")
@admin_required
def newsletter_new():
    latest = nl.get_latest_newsletter()
    today = date.today()

    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)

    if not year or not month:
        if latest:
            year, month = latest["year"], latest["month"]
            month += 1
            if month > 12:
                month = 1
                year += 1
        else:
            year, month = today.year, today.month

    data = nl.build_default_data(ACADEMY_NAME, year, month, carry_over=latest)
    newsletter_id = nl.create_newsletter(year, month, data)
    flash(f"{year}년 {month}월 알림장 초안을 만들었습니다. 내용을 채우고 저장해주세요.", "success")
    return redirect(url_for("newsletter_edit", newsletter_id=newsletter_id))


def _save_qr_image(file_storage, newsletter_id):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(secure_filename(file_storage.filename))[1].lower() or ".png"
    if ext not in (".png", ".jpg", ".jpeg"):
        ext = ".png"
    filename = f"qr_{newsletter_id}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    file_storage.save(path)
    return path


@app.route("/admin/newsletters/<int:newsletter_id>/edit")
@admin_required
def newsletter_edit(newsletter_id):
    data = nl.get_newsletter(newsletter_id)
    if not data:
        abort(404)
    return render_template(
        "admin_newsletter_form.html",
        newsletter=data,
        year=data["year"],
        month=data["month"],
        is_new=False,
        newsletter_id=newsletter_id,
    )


@app.route("/admin/newsletters/<int:newsletter_id>", methods=["POST"])
@admin_required
def newsletter_update(newsletter_id):
    check_csrf()
    existing = nl.get_newsletter(newsletter_id)
    if not existing:
        abort(404)

    existing_qr_path = existing.get("tuition", {}).get("qr_image_path")
    data = _parse_newsletter_form(request.form, existing_qr_path=existing_qr_path)

    qr_file = request.files.get("qr_image")
    if qr_file and qr_file.filename:
        data["tuition"]["qr_image_path"] = _save_qr_image(qr_file, newsletter_id)
    if request.form.get("remove_qr_image") == "1":
        data["tuition"]["qr_image_path"] = None

    nl.update_newsletter(newsletter_id, data)
    flash("알림장이 저장되었습니다.", "success")
    return redirect(url_for("newsletter_edit", newsletter_id=newsletter_id))


@app.route("/admin/newsletters/<int:newsletter_id>/delete", methods=["POST"])
@admin_required
def newsletter_delete(newsletter_id):
    check_csrf()
    nl.delete_newsletter(newsletter_id)
    flash("알림장이 삭제되었습니다.", "success")
    return redirect(url_for("newsletter_list"))


@app.route("/admin/newsletters/<int:newsletter_id>/regenerate/<field>", methods=["POST"])
@admin_required
def newsletter_regenerate(newsletter_id, field):
    check_csrf()
    data = nl.get_newsletter(newsletter_id)
    if not data:
        abort(404)

    seed_bump = request.form.get("seed", "0")
    if field == "director":
        import random as _r
        pool_seed = f"{data['year']}-{data['month']}-director-{seed_bump}"
        from content_bank import DIRECTOR_MESSAGES
        options = DIRECTOR_MESSAGES.get(data["month"], DIRECTOR_MESSAGES[1])
        data["director_message"] = _r.Random(pool_seed).choice(options)
    elif field == "quote":
        import random as _r
        pool_seed = f"{data['year']}-{data['month']}-quote-{seed_bump}"
        from content_bank import QUOTES
        q = _r.Random(pool_seed).choice(QUOTES)
        data["quote_text"], data["quote_author"] = q
    else:
        abort(404)

    nl.update_newsletter(newsletter_id, data)
    return redirect(url_for("newsletter_edit", newsletter_id=newsletter_id) + "#" + field)


@app.route("/admin/newsletters/<int:newsletter_id>/preview")
@admin_required
def newsletter_preview(newsletter_id):
    data = nl.get_newsletter(newsletter_id)
    if not data:
        abort(404)
    return render_flyer_html(data)


@app.route("/admin/newsletters/<int:newsletter_id>/download")
@admin_required
def newsletter_download(newsletter_id):
    data = nl.get_newsletter(newsletter_id)
    if not data:
        abort(404)
    fd, tmp_path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    render_flyer_png(data, tmp_path)
    download_name = f"{data['academy_name']}_{data['year']}년{data['month']}월_알림장.png"
    return send_file(
        tmp_path,
        mimetype="image/png",
        as_attachment=True,
        download_name=download_name,
    )


def _parse_score_form():
    errors = []

    parent_id = request.form.get("parent_id", "").strip()
    parent = None
    if not parent_id:
        errors.append("학생(학부모 계정)을 선택해주세요.")
    else:
        try:
            parent_id = int(parent_id)
            parent = models.get_user_by_id(parent_id)
        except ValueError:
            parent_id = None
        if not parent or parent.role != "parent":
            errors.append("선택한 학생 계정을 찾을 수 없습니다.")

    exam_type = request.form.get("exam_type", "").strip()
    if exam_type not in scores.EXAM_TYPES:
        errors.append("시험 종류를 선택해주세요.")

    subject = request.form.get("subject", "").strip()
    if not subject:
        errors.append("과목을 입력해주세요.")

    score_raw = request.form.get("score", "").strip()
    max_score_raw = request.form.get("max_score", "").strip() or "100"
    score_val = None
    max_score_val = None
    try:
        score_val = float(score_raw)
    except ValueError:
        errors.append("점수는 숫자로 입력해주세요.")
    try:
        max_score_val = float(max_score_raw)
    except ValueError:
        errors.append("만점은 숫자로 입력해주세요.")
    if score_val is not None and max_score_val is not None and score_val > max_score_val:
        errors.append("점수가 만점보다 클 수 없습니다.")

    exam_date = request.form.get("exam_date", "").strip() or None
    note = request.form.get("note", "").strip() or None

    return {
        "errors": errors,
        "parent_id": parent_id if isinstance(parent_id, int) else None,
        "exam_type": exam_type,
        "subject": subject,
        "score": score_val,
        "max_score": max_score_val,
        "exam_date": exam_date,
        "note": note,
    }


@app.route("/admin/scores")
@admin_required
def scores_list():
    parent_id = request.args.get("parent_id", type=int)
    parents = models.list_parents()
    score_rows = scores.list_scores(parent_id=parent_id)
    return render_template(
        "admin_scores_list.html",
        scores=score_rows,
        parents=parents,
        selected_parent_id=parent_id,
        exam_types=scores.EXAM_TYPES,
    )


@app.route("/admin/scores/new", methods=["GET", "POST"])
@admin_required
def scores_new():
    parents = models.list_parents()

    if request.method == "POST":
        check_csrf()
        data = _parse_score_form()
        if data["errors"]:
            for e in data["errors"]:
                flash(e, "error")
            return render_template(
                "admin_scores_form.html",
                parents=parents,
                score=None,
                is_new=True,
                exam_types=scores.EXAM_TYPES,
                subject_suggestions=scores.SUBJECT_SUGGESTIONS,
                form_data=data,
            )
        scores.create_score(
            parent_id=data["parent_id"],
            exam_type=data["exam_type"],
            subject=data["subject"],
            score=data["score"],
            max_score=data["max_score"],
            exam_date=data["exam_date"],
            note=data["note"],
            created_by=g.user.id,
        )
        flash("성적이 등록되었습니다.", "success")
        return redirect(url_for("scores_list"))

    default_parent_id = request.args.get("parent_id", type=int)
    return render_template(
        "admin_scores_form.html",
        parents=parents,
        score=None,
        is_new=True,
        exam_types=scores.EXAM_TYPES,
        subject_suggestions=scores.SUBJECT_SUGGESTIONS,
        form_data={"parent_id": default_parent_id} if default_parent_id else None,
    )


@app.route("/admin/scores/<int:score_id>/edit", methods=["GET", "POST"])
@admin_required
def scores_edit(score_id):
    score = scores.get_score(score_id)
    if not score:
        abort(404)
    parents = models.list_parents()

    if request.method == "POST":
        check_csrf()
        data = _parse_score_form()
        if data["errors"]:
            for e in data["errors"]:
                flash(e, "error")
            return render_template(
                "admin_scores_form.html",
                parents=parents,
                score=score,
                is_new=False,
                exam_types=scores.EXAM_TYPES,
                subject_suggestions=scores.SUBJECT_SUGGESTIONS,
                form_data=data,
            )
        scores.update_score(
            score_id,
            parent_id=data["parent_id"],
            exam_type=data["exam_type"],
            subject=data["subject"],
            score=data["score"],
            max_score=data["max_score"],
            exam_date=data["exam_date"],
            note=data["note"],
        )
        flash("성적이 수정되었습니다.", "success")
        return redirect(url_for("scores_list"))

    return render_template(
        "admin_scores_form.html",
        parents=parents,
        score=score,
        is_new=False,
        exam_types=scores.EXAM_TYPES,
        subject_suggestions=scores.SUBJECT_SUGGESTIONS,
        form_data=None,
    )


@app.route("/admin/scores/<int:score_id>/delete", methods=["POST"])
@admin_required
def scores_delete(score_id):
    check_csrf()
    scores.delete_score(score_id)
    flash("성적이 삭제되었습니다.", "success")
    return redirect(url_for("scores_list"))


@app.route("/dashboard")
@parent_required
def parent_dashboard():
    score_rows = scores.list_scores(parent_id=g.user.id)
    subject_trends = scores.build_subject_trends(score_rows)
    overall_avg = None
    if subject_trends:
        overall_avg = round(sum(t["latest_pct"] for t in subject_trends) / len(subject_trends), 1)
    return render_template(
        "parent_dashboard.html",
        score_rows=score_rows,
        subject_trends=subject_trends,
        overall_avg=overall_avg,
    )


@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403, message="접근 권한이 없습니다."), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="페이지를 찾을 수 없습니다."), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
