import sqlite3
import json
import logging
from config import DB_FILE

log = logging.getLogger(__name__)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS orders (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL,

            room_type      TEXT NOT NULL,
            area           REAL NOT NULL,
            cleaning_type  TEXT NOT NULL,
            is_one_time    INTEGER NOT NULL DEFAULT 1,
            extra_services TEXT NOT NULL DEFAULT '[]',

            contact_name   TEXT NOT NULL,
            contact_phone  TEXT NOT NULL,
            address        TEXT NOT NULL,

            photos         TEXT NOT NULL DEFAULT '[]',

            price          REAL,
            priority       TEXT NOT NULL DEFAULT 'medium',

            status         TEXT NOT NULL DEFAULT 'new',
            admin_comment  TEXT,

            created_at     TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at     TEXT DEFAULT (datetime('now', 'localtime')),

            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS status_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id    INTEGER NOT NULL,
            old_status  TEXT,
            new_status  TEXT NOT NULL,
            changed_by  INTEGER,
            changed_at  TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );

        CREATE INDEX IF NOT EXISTS ix_orders_user_id  ON orders(user_id);
        CREATE INDEX IF NOT EXISTS ix_orders_status   ON orders(status);
        CREATE INDEX IF NOT EXISTS ix_orders_created  ON orders(created_at);
        """)
    log.info("База данных инициализирована: %s", DB_FILE)


def save_user(user_id: int, username: str, first_name: str, last_name: str) -> None:
    with connect() as db:
        db.execute("""
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name
        """, (user_id, username or "", first_name or "", last_name or ""))


def get_user(user_id: int):
    with connect() as db:
        return db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()


def create_order(data: dict) -> int:
    extras_json = json.dumps(data.get("extra_services", []), ensure_ascii=False)
    photos_json = json.dumps(data.get("photos", []), ensure_ascii=False)
    initial_status = data.get("status", "new")

    with connect() as db:
        cur = db.execute("""
            INSERT INTO orders (
                user_id, room_type, area, cleaning_type, is_one_time,
                extra_services, contact_name, contact_phone, address,
                photos, price, priority, status, admin_comment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["user_id"],
            data["room_type"],
            data["area"],
            data["cleaning_type"],
            1 if data["is_one_time"] else 0,
            extras_json,
            data["contact_name"],
            data["contact_phone"],
            data["address"],
            photos_json,
            data.get("price"),
            data.get("priority", "medium"),
            initial_status,
            data.get("admin_comment"),
        ))
        order_id = cur.lastrowid

        db.execute("""
            INSERT INTO status_history (order_id, old_status, new_status, changed_by)
            VALUES (?, NULL, ?, ?)
        """, (order_id, initial_status, data["user_id"]))

    log.info("Создана заявка #%d (user_id=%d)", order_id, data["user_id"])
    return order_id


def get_order(order_id: int):
    with connect() as db:
        return db.execute(
            "SELECT * FROM orders WHERE id = ?",
            (order_id,)
        ).fetchone()


def get_orders_by_user(user_id: int) -> list:
    with connect() as db:
        return db.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()


def get_all_orders(status: str | None = None) -> list:
    with connect() as db:
        if status:
            return db.execute(
                "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC",
                (status,)
            ).fetchall()
        return db.execute(
            "SELECT * FROM orders ORDER BY created_at DESC"
        ).fetchall()


def update_status(order_id: int, new_status: str, admin_id: int, comment: str = None) -> int | None:
    with connect() as db:
        row = db.execute(
            "SELECT status, user_id FROM orders WHERE id = ?",
            (order_id,)
        ).fetchone()

        if not row:
            return None

        old_status = row["status"]
        user_id = row["user_id"]

        db.execute("""
            UPDATE orders
            SET status = ?,
                admin_comment = COALESCE(?, admin_comment),
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
        """, (new_status, comment, order_id))

        db.execute("""
            INSERT INTO status_history (order_id, old_status, new_status, changed_by)
            VALUES (?, ?, ?, ?)
        """, (order_id, old_status, new_status, admin_id))

    log.info("Заявка #%d: %s → %s (admin=%d)", order_id, old_status, new_status, admin_id)
    return user_id


def get_analytics() -> dict:
    with connect() as db:
        total = db.execute("SELECT COUNT(*) FROM orders").fetchone()[0]

        by_status = db.execute("""
            SELECT status, COUNT(*) AS cnt
            FROM orders
            GROUP BY status
            ORDER BY cnt DESC
        """).fetchall()

        top_services = db.execute("""
            SELECT cleaning_type, COUNT(*) AS cnt
            FROM orders
            GROUP BY cleaning_type
            ORDER BY cnt DESC
            LIMIT 5
        """).fetchall()

        avg_area = db.execute(
            "SELECT ROUND(AVG(area), 1) FROM orders"
        ).fetchone()[0] or 0

        avg_price = db.execute(
            "SELECT ROUND(AVG(price), 0) FROM orders WHERE price IS NOT NULL"
        ).fetchone()[0] or 0

        today = db.execute("""
            SELECT COUNT(*) FROM orders
            WHERE date(created_at) = date('now', 'localtime')
        """).fetchone()[0]

        week = db.execute("""
            SELECT COUNT(*) FROM orders
            WHERE created_at >= datetime('now', '-7 days', 'localtime')
        """).fetchone()[0]

        total_revenue = db.execute("""
            SELECT ROUND(SUM(price), 0)
            FROM orders
            WHERE price IS NOT NULL AND status = 'done'
        """).fetchone()[0] or 0

    return {
        "total": total,
        "by_status": [(r["status"], r["cnt"]) for r in by_status],
        "top_services": [(r["cleaning_type"], r["cnt"]) for r in top_services],
        "avg_area": avg_area,
        "avg_price": avg_price,
        "today": today,
        "week": week,
        "total_revenue": total_revenue,
    }