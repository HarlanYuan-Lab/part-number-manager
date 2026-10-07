"""Account / role authentication for the application login.

Accounts live in the central `users` table. The database connection itself uses
the server's DB role (see config); the *application* login (username + password)
is validated against this table and grants a role.

NOTE (open-source): the two default accounts below are EXAMPLES. Change the
usernames and, above all, the passwords before you deploy:

    - admin  (admin / CHANGE_ME_ADMIN_PASSWORD): full access.
    - user   (user1 / CHANGE_ME_USER_PASSWORD) : regular personal account.
"""

from __future__ import annotations

import hashlib
import secrets

from .db import ConnectionManager

DEFAULT_USERS = {
    # username: (plain password, role)
    "admin": ("CHANGE_ME_ADMIN_PASSWORD", "admin"),
    "user1": ("CHANGE_ME_USER_PASSWORD", "user"),
}

_ITERATIONS = 100_000


def hash_password(plain: str, salt_hex: str | None = None) -> str:
    salt = salt_hex or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"),
                             bytes.fromhex(salt), _ITERATIONS)
    return f"{salt}${dk.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"),
                                 bytes.fromhex(salt), _ITERATIONS)
        return dk.hex() == expected
    except Exception:
        return False


class UserService:
    """Manage users on the server and validate logins."""

    def __init__(self, db: ConnectionManager) -> None:
        self.db = db

    def ensure_default_users(self) -> None:
        today = "2026-10-06"
        for username, (plain, role) in DEFAULT_USERS.items():
            self.db.execute(
                "INSERT INTO users (username, password_hash, role, created_date) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (username) DO NOTHING",
                (username, hash_password(plain), role, today))

    def login(self, username: str, password: str) -> tuple[str, str]:
        """Validate credentials. Returns (username, role) or raises ValueError."""
        username = username.strip()
        if not username or not password:
            raise ValueError("Please enter a username and password.")
        row = self.db.execute_one(
            "SELECT username, password_hash, role FROM users "
            "WHERE username = %s", (username,))
        if row is None or not verify_password(password, row["password_hash"]):
            raise ValueError("Invalid username or password.")
        return row["username"], row["role"]

    # ------------------------------------------------------------------ admin
    def create_user(self, username: str, password: str, role: str = "user") -> None:
        username = username.strip()
        if not username:
            raise ValueError("Username must not be empty.")
        if not password:
            raise ValueError("Password must not be empty.")
        if role not in ("admin", "user"):
            role = "user"
        exists = self.db.execute_one(
            "SELECT 1 AS x FROM users WHERE username = %s", (username,))
        if exists:
            raise ValueError(f"Username '{username}' already exists.")
        today = "2026-10-06"
        self.db.execute(
            "INSERT INTO users (username, password_hash, role, created_date) "
            "VALUES (%s, %s, %s, %s)",
            (username, hash_password(password), role, today))

    def list_users(self) -> list:
        return self.db.execute(
            "SELECT username, role, created_date FROM users "
            "ORDER BY username")

    def set_role(self, username: str, role: str) -> None:
        if role not in ("admin", "user"):
            raise ValueError("Role must be 'admin' or 'user'.")
        self.db.execute(
            "UPDATE users SET role = %s WHERE username = %s", (role, username))

    def reset_password(self, username: str, new_password: str) -> None:
        if not new_password:
            raise ValueError("Password must not be empty.")
        self.db.execute(
            "UPDATE users SET password_hash = %s WHERE username = %s",
            (hash_password(new_password), username))

    def delete_user(self, username: str) -> None:
        self.db.execute("DELETE FROM users WHERE username = %s", (username,))
