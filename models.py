from werkzeug.security import generate_password_hash, check_password_hash

from db import db_cursor


class User:
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.password_hash = row["password_hash"]
        self.role = row["role"]
        self.name = row["name"]
        self.student_name = row["student_name"]
        self.created_at = row["created_at"]

    @property
    def is_admin(self):
        return self.role == "admin"


def get_user_by_username(username):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        return User(row) if row else None


def get_user_by_id(user_id):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return User(row) if row else None


def verify_password(user, password):
    return check_password_hash(user.password_hash, password)


def create_user(username, password, role, name, student_name=None):
    password_hash = generate_password_hash(password)
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO users (username, password_hash, role, name, student_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, password_hash, role, name, student_name),
        )
        return cur.lastrowid


def list_parents():
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM users WHERE role = 'parent' ORDER BY created_at DESC"
        )
        return [User(row) for row in cur.fetchall()]


def username_exists(username):
    with db_cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        return cur.fetchone() is not None


def delete_user(user_id):
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM users WHERE id = ? AND role = 'parent'", (user_id,))


def reset_password(user_id, new_password):
    password_hash = generate_password_hash(new_password)
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (password_hash, user_id),
        )
