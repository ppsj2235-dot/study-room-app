"""
DB 접근 헬퍼.

기본은 SQLite(파일 DB)를 쓰지만, 환경변수 DATABASE_URL이 설정되어 있으면
PostgreSQL(Neon 등 무료 호스팅)을 대신 사용합니다. Render 같은 배포 환경에서는
재배포할 때마다 SQLite 파일이 초기화되기 때문에, 실제 운영에서는 DATABASE_URL을
설정해서 PostgreSQL을 쓰는 걸 권장합니다.

models.py / models_newsletter.py / models_scores.py는 이 파일이 제공하는
db_cursor()만 사용하고, SQLite와 PostgreSQL의 차이(플레이스홀더 `?` vs `%s`,
새로 생성된 id를 가져오는 방식)는 전부 이 파일 안에서만 처리합니다. 즉, 위
파일들의 쿼리 코드는 두 DB 어디에서 실행되든 그대로 동작합니다.
"""
import os
import sqlite3
import threading
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL")  # 설정되어 있으면 PostgreSQL 사용
IS_PG = bool(DATABASE_URL)

DB_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "app.db"),
)

if IS_PG:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool

    # Neon 같은 원격 PostgreSQL은 매번 새로 연결을 맺을 때(TCP+TLS+인증)
    # 1~3초 가까이 걸릴 수 있습니다. 화면 하나를 열 때마다 쿼리를 2~3번씩 날리는데
    # 그때마다 새 연결을 맺으면 페이지 하나 여는 데 수 초씩 걸리게 됩니다.
    # 그래서 연결을 몇 개 미리 만들어두고 재사용하는 커넥션 풀을 씁니다.
    _pg_pool = None
    _pg_pool_lock = threading.Lock()

    def _get_pool():
        global _pg_pool
        if _pg_pool is None:
            with _pg_pool_lock:
                if _pg_pool is None:
                    _pg_pool = psycopg2.pool.ThreadedConnectionPool(
                        1,
                        int(os.environ.get("DB_POOL_MAX", "5")),
                        dsn=DATABASE_URL,
                        cursor_factory=psycopg2.extras.RealDictCursor,
                    )
        return _pg_pool


class _PGCursor:
    """PostgreSQL용 커서 래퍼.

    - SQLite 스타일 플레이스홀더(`?`)를 PostgreSQL 스타일(`%s`)로 자동 변환합니다.
    - INSERT 문에는 자동으로 `RETURNING id`를 붙이고, 실행 결과를 `lastrowid`로
      노출해서 sqlite3의 `cursor.lastrowid`와 동일하게 쓸 수 있게 합니다.
    """

    def __init__(self, raw_cursor):
        self._cur = raw_cursor
        self.lastrowid = None

    def execute(self, sql, params=()):
        translated = sql.replace("?", "%s")
        stripped = translated.strip().upper()
        is_insert = stripped.startswith("INSERT INTO")
        if is_insert and "RETURNING" not in stripped:
            translated = translated.rstrip().rstrip(";") + " RETURNING id"
        self._cur.execute(translated, params)
        if is_insert:
            row = self._cur.fetchone()
            self.lastrowid = row["id"] if row else None
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def __getattr__(self, name):
        return getattr(self._cur, name)


def get_connection():
    if IS_PG:
        return _get_pool().getconn()
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_cursor(commit=False):
    if not IS_PG:
        conn = get_connection()
        try:
            yield conn.cursor()
            if commit:
                conn.commit()
        finally:
            conn.close()
        return

    # PostgreSQL: 풀에서 연결을 빌려쓰고 끝나면 닫지 않고 풀에 반납해서 재사용합니다.
    # (연결을 새로 맺을 때마다 Neon까지 왕복하는 비용이 커서, 매번 새로 열면
    #  화면 하나 여는 데도 몇 초씩 걸립니다.)
    pool = _get_pool()
    conn = pool.getconn()
    conn_is_bad = False
    try:
        raw_cur = conn.cursor()
        cur = _PGCursor(raw_cur)
        yield cur
        if commit:
            conn.commit()
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        # 연결 자체가 끊어진 경우(장시간 미사용 후 등) - 풀에 돌려주지 않고 버립니다.
        conn_is_bad = True
        raise
    except Exception:
        try:
            conn.rollback()
        except Exception:
            conn_is_bad = True
        raise
    finally:
        pool.putconn(conn, close=conn_is_bad)


# SQLite는 "INTEGER PRIMARY KEY AUTOINCREMENT", PostgreSQL은 "SERIAL PRIMARY KEY"
_PK = "SERIAL PRIMARY KEY" if IS_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"


def init_db():
    with db_cursor(commit=True) as cur:
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS users (
                id {_PK},
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'parent')),
                name TEXT NOT NULL,
                student_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # 다음 단계(알림장 / 학습 평가표)를 위해 테이블은 미리 만들어두되
        # 아직 화면/기능은 연결하지 않습니다. (요청하신 대로 로그인부터 우선 진행)
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS notices (
                id {_PK},
                title TEXT NOT NULL,
                file_path TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                uploaded_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS reports (
                id {_PK},
                parent_id INTEGER NOT NULL REFERENCES users(id),
                title TEXT NOT NULL,
                file_path TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                uploaded_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS newsletters (
                id {_PK},
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # 중간고사 / 기말고사 / 월말고사 성적 (숫자 점수) - 관리자만 등록/수정 가능
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS exam_scores (
                id {_PK},
                parent_id INTEGER NOT NULL REFERENCES users(id),
                exam_type TEXT NOT NULL,
                subject TEXT NOT NULL,
                score REAL NOT NULL,
                max_score REAL NOT NULL DEFAULT 100,
                exam_date TEXT,
                note TEXT,
                created_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
