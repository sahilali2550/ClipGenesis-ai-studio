import os
import sqlite3
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
from app.utils import utils
from assets.schemas import AssetItem, AssetQuery


DB_DIR = os.path.join(utils.root_dir(), "assets", "database")
DB_PATH = os.path.join(DB_DIR, "assets.db")


def get_db_path() -> str:
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)
    return DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes SQLite database and creates assets table if not exists."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            path TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            tags TEXT DEFAULT '',
            duration REAL DEFAULT 0.0,
            width INTEGER DEFAULT 0,
            height INTEGER DEFAULT 0,
            format TEXT DEFAULT '',
            favorite INTEGER DEFAULT 0,
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def row_to_item(row: sqlite3.Row) -> AssetItem:
    tag_list = [t.strip() for t in row["tags"].split(",") if t.strip()] if row["tags"] else []
    return AssetItem(
        id=row["id"],
        asset_id=row["asset_id"],
        filename=row["filename"],
        path=row["path"],
        type=row["type"],
        category=row["category"],
        tags=tag_list,
        duration=row["duration"],
        width=row["width"],
        height=row["height"],
        format=row["format"],
        favorite=bool(row["favorite"]),
        usage_count=row["usage_count"],
        created_at=str(row["created_at"]),
    )


def register_asset(item: AssetItem) -> AssetItem:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    if not item.asset_id:
        item.asset_id = f"ast_{uuid.uuid4().hex[:8]}"

    tag_str = ",".join(item.tags) if item.tags else ""
    
    cursor.execute("""
        INSERT INTO assets (asset_id, filename, path, type, category, tags, duration, width, height, format, favorite, usage_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            filename=excluded.filename,
            type=excluded.type,
            category=excluded.category,
            tags=excluded.tags,
            duration=excluded.duration,
            width=excluded.width,
            height=excluded.height,
            format=excluded.format
    """, (
        item.asset_id, item.filename, item.path, item.type, item.category,
        tag_str, item.duration, item.width, item.height, item.format,
        1 if item.favorite else 0, item.usage_count
    ))

    conn.commit()

    # Fetch saved record
    cursor.execute("SELECT * FROM assets WHERE path = ?", (item.path,))
    row = cursor.fetchone()
    conn.close()
    return row_to_item(row)


def get_asset_by_id(asset_id: str) -> Optional[AssetItem]:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM assets WHERE asset_id = ? OR path = ?", (asset_id, asset_id))
    row = cursor.fetchone()
    conn.close()
    return row_to_item(row) if row else None


def search_assets(q: AssetQuery) -> List[AssetItem]:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    sql = "SELECT * FROM assets WHERE 1=1"
    params = []

    if q.query:
        sql += " AND (filename LIKE ? OR tags LIKE ?)"
        params.extend([f"%{q.query}%", f"%{q.query}%"])

    if q.asset_type:
        sql += " AND type = ?"
        params.append(q.asset_type)

    if q.category:
        sql += " AND category = ?"
        params.append(q.category)

    if q.tag:
        sql += " AND tags LIKE ?"
        params.append(f"%{q.tag}%")

    if q.favorite_only:
        sql += " AND favorite = 1"

    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([q.limit, q.offset])

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [row_to_item(r) for r in rows]


def get_asset_stats() -> Dict[str, int]:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {"total": 0, "image": 0, "video": 0, "audio": 0, "voice": 0}
    cursor.execute("SELECT type, COUNT(*) as count FROM assets GROUP BY type")
    rows = cursor.fetchall()
    
    for r in rows:
        t = r["type"]
        cnt = r["count"]
        if t in stats:
            stats[t] = cnt
        stats["total"] += cnt
        
    conn.close()
    return stats
