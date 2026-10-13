import sqlite3
from typing import Optional

def get_connection(db_path: str = "orders.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = "orders.db") -> None:
    conn = get_connection(db_path)
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            name TEXT,
            raw_phone TEXT,
            normalized_phone TEXT,
            email TEXT,
            amount REAL,
            created_at TEXT,
            is_valid INTEGER,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS clients (
            phone TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            amount REAL,
            source_order_id INTEGER,
            source_created_at TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sync_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            received INTEGER,
            unique_clients INTEGER,
            duplicates_merged INTEGER,
            invalid_dropped INTEGER,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
    conn.close()
