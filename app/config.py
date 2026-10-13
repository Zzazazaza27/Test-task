import os
from pydantic import BaseModel

class Settings(BaseModel):
    orders_api_url: str = os.getenv("ORDERS_API_URL", "https://test.ooobs.ru/api/orders")
    db_path: str = os.getenv("DB_PATH", "orders.db")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8080"))
    sync_timeout_sec: float = float(os.getenv("SYNC_TIMEOUT_SEC", "10.0"))

settings = Settings()
