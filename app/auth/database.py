"""用户数据库模块 —— SQLite + aiosqlite"""

import os
from pathlib import Path
from typing import Optional

import aiosqlite
import bcrypt

from app.config import settings

DB_PATH = str(Path(settings.CHROMA_PERSIST_DIR).parent / "users.db")


def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """验证密码与哈希是否匹配"""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


async def get_db() -> aiosqlite.Connection:
    """获取数据库连接"""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db() -> None:
    """初始化数据库表并预置账号"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await get_db()
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    NOT NULL UNIQUE,
                password_hash TEXT  NOT NULL,
                role        TEXT    NOT NULL DEFAULT 'user',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await db.commit()

        # 预置账号（仅首次）
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        if row and row[0] == 0:
            await _seed_users(db)
    finally:
        await db.close()


async def _seed_users(db: aiosqlite.Connection) -> None:
    """写入预置账号: admin / user"""
    users = [
        ("admin", "admin123", "admin"),
        ("user",  "user123",  "user"),
    ]
    for username, password, role in users:
        hashed = hash_password(password)
        await db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, hashed, role),
        )
    await db.commit()


async def verify_user(username: str, password: str) -> Optional[dict]:
    """验证用户名密码，成功返回用户信息，失败返回 None"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, username, role, password_hash FROM users WHERE username = ?",
            (username,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None

        if not verify_password(password, row["password_hash"]):
            return None

        return {"id": row["id"], "username": row["username"], "role": row["role"]}
    finally:
        await db.close()


# ==================== 管理员：用户管理 ====================

async def list_users() -> list[dict]:
    """获取所有用户列表（不含密码哈希）"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, username, role, created_at FROM users ORDER BY id"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def create_user(username: str, password: str, role: str = "user") -> dict:
    """创建新用户，返回用户信息"""
    db = await get_db()
    try:
        hashed = hash_password(password)
        await db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, hashed, role),
        )
        await db.commit()
        return {"username": username, "role": role}
    except aiosqlite.IntegrityError:
        raise ValueError(f"用户名 '{username}' 已存在")
    finally:
        await db.close()


async def update_user_role(username: str, role: str) -> bool:
    """修改用户角色"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "UPDATE users SET role = ? WHERE username = ?",
            (role, username),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def reset_user_password(username: str, new_password: str) -> bool:
    """重置用户密码"""
    db = await get_db()
    try:
        hashed = hash_password(new_password)
        cursor = await db.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (hashed, username),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def delete_user(username: str) -> bool:
    """删除用户（不能删除最后一个 admin）"""
    db = await get_db()
    try:
        # 检查是否最后一个 admin
        cursor = await db.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'admin'"
        )
        row = await cursor.fetchone()
        admin_count = row[0] if row else 0

        target = await db.execute(
            "SELECT role FROM users WHERE username = ?", (username,)
        )
        target_row = await target.fetchone()
        if target_row and target_row["role"] == "admin" and admin_count <= 1:
            raise ValueError("不能删除最后一个管理员账号")

        cursor = await db.execute("DELETE FROM users WHERE username = ?", (username,))
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def get_user_count() -> int:
    """获取用户总数"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        return row[0] if row else 0
    finally:
        await db.close()
