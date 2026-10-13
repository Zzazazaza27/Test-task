import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import httpx

from app.config import settings
from app.database import get_connection, init_db
from app.models import ClientResponse, RawOrder, StatsResponse, SyncResultResponse
from app.normalizer import normalize_phone

logger = logging.getLogger(__name__)

def parse_created_at(ts_str: Optional[str]) -> datetime:
    """Parses ISO timestamp safely, returning UTC datetime."""
    if not ts_str:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    try:
        clean_ts = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.fromtimestamp(0, tz=timezone.utc)

class OrderSynchronizer:
    def __init__(self, db_path: Optional[str] = None, api_url: Optional[str] = None):
        self.db_path = db_path or settings.db_path
        self.api_url = api_url or settings.orders_api_url
        init_db(self.db_path)

    async def fetch_raw_orders(self) -> List[Dict[str, Any]]:
        """Fetches raw orders from the upstream API endpoint."""
        async with httpx.AsyncClient(timeout=settings.sync_timeout_sec) as client:
            response = await client.get(self.api_url)
            response.raise_for_status()
            return response.json()

    def process_and_deduplicate(
        self, raw_data: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], StatsResponse]:
        """
        Normalizes and deduplicates orders.
        
        Rules:
        1. Phones are normalized to +7XXXXXXXXXX. Non-11-digit numbers are dropped.
        2. Duplicates by phone:
           - Record with maximum amount wins.
           - Tie-break: record with later created_at timestamp wins.
        """
        received = len(raw_data)
        invalid_dropped = 0
        phone_groups: Dict[str, List[Dict[str, Any]]] = {}

        for item in raw_data:
            phone_norm = normalize_phone(item.get("phone"))
            if not phone_norm:
                invalid_dropped += 1
                continue

            if phone_norm not in phone_groups:
                phone_groups[phone_norm] = []
            
            phone_groups[phone_norm].append(item)

        unique_clients = len(phone_groups)
        duplicates_merged = sum(len(group) - 1 for group in phone_groups.values())

        # Select winner for each phone group
        winning_clients: List[Dict[str, Any]] = []
        for phone, group in phone_groups.items():
            # Sort group by amount DESC, then created_at DESC
            winner = max(
                group,
                key=lambda o: (
                    float(o.get("amount") or 0),
                    parse_created_at(o.get("created_at")),
                ),
            )
            winning_clients.append({
                "name": winner.get("name") or "",
                "phone": phone,
                "email": winner.get("email") or "",
                "amount": winner.get("amount") if winner.get("amount") is not None else 0,
                "source_order_id": winner.get("id"),
                "source_created_at": winner.get("created_at"),
            })

        stats = StatsResponse(
            received=received,
            unique=unique_clients,
            duplicates_merged=duplicates_merged,
            invalid_dropped=invalid_dropped,
        )

        return raw_data, winning_clients, stats

    def save_to_db(
        self,
        raw_data: List[Dict[str, Any]],
        winning_clients: List[Dict[str, Any]],
        stats: StatsResponse,
    ) -> None:
        """Idempotently saves orders, deduplicated clients, and sync run stats to SQLite."""
        conn = get_connection(self.db_path)
        with conn:
            # 1. Upsert raw orders
            for item in raw_data:
                order_id = item.get("id")
                norm_phone = normalize_phone(item.get("phone"))
                is_valid = 1 if norm_phone else 0
                conn.execute(
                    """
                    INSERT INTO orders (id, name, raw_phone, normalized_phone, email, amount, created_at, is_valid)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        raw_phone=excluded.raw_phone,
                        normalized_phone=excluded.normalized_phone,
                        email=excluded.email,
                        amount=excluded.amount,
                        created_at=excluded.created_at,
                        is_valid=excluded.is_valid,
                        synced_at=CURRENT_TIMESTAMP;
                    """,
                    (
                        order_id,
                        item.get("name") or "",
                        item.get("phone") or "",
                        norm_phone,
                        item.get("email") or "",
                        float(item.get("amount") or 0),
                        item.get("created_at") or "",
                        is_valid,
                    ),
                )

            # 2. Update clients table
            conn.execute("DELETE FROM clients;")
            for c in winning_clients:
                conn.execute(
                    """
                    INSERT INTO clients (phone, name, email, amount, source_order_id, source_created_at)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (
                        c["phone"],
                        c["name"],
                        c["email"],
                        c["amount"],
                        c.get("source_order_id"),
                        c.get("source_created_at"),
                    ),
                )

            # 3. Record sync run
            conn.execute(
                """
                INSERT INTO sync_history (received, unique_clients, duplicates_merged, invalid_dropped)
                VALUES (?, ?, ?, ?);
                """,
                (
                    stats.received,
                    stats.unique,
                    stats.duplicates_merged,
                    stats.invalid_dropped,
                ),
            )
        conn.close()

    def get_latest_from_db(self) -> Optional[SyncResultResponse]:
        """Retrieves the latest synchronized state from the database."""
        conn = get_connection(self.db_path)
        last_sync = conn.execute(
            "SELECT * FROM sync_history ORDER BY id DESC LIMIT 1"
        ).fetchone()

        if not last_sync:
            conn.close()
            return None

        clients_rows = conn.execute(
            "SELECT name, phone, email, amount FROM clients"
        ).fetchall()
        conn.close()

        clients = [
            ClientResponse(
                name=row["name"],
                phone=row["phone"],
                email=row["email"],
                amount=row["amount"],
            )
            for row in clients_rows
        ]

        stats = StatsResponse(
            received=last_sync["received"],
            unique=last_sync["unique_clients"],
            duplicates_merged=last_sync["duplicates_merged"],
            invalid_dropped=last_sync["invalid_dropped"],
        )

        return SyncResultResponse(clients=clients, stats=stats)

    async def synchronize(self) -> SyncResultResponse:
        """Fetches from API, processes, saves to DB, and returns result."""
        raw_data = await self.fetch_raw_orders()
        _, winning_clients, stats = self.process_and_deduplicate(raw_data)
        self.save_to_db(raw_data, winning_clients, stats)

        clients_resp = [
            ClientResponse(
                name=c["name"],
                phone=c["phone"],
                email=c["email"],
                amount=c["amount"],
            )
            for c in winning_clients
        ]

        return SyncResultResponse(clients=clients_resp, stats=stats)
