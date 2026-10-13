from typing import List, Optional, Union
from pydantic import BaseModel, Field

class RawOrder(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = ""
    phone: Optional[str] = None
    email: Optional[str] = ""
    amount: Union[int, float] = 0
    created_at: Optional[str] = None

class ClientResponse(BaseModel):
    name: str = ""
    phone: str
    email: str = ""
    amount: Union[int, float] = 0

class StatsResponse(BaseModel):
    received: int = Field(..., description="Сколько заявок получено из /api/orders")
    unique: int = Field(..., description="Уникальных клиентов в итоге")
    duplicates_merged: int = Field(..., description="Сколько дублей схлопнуто")
    invalid_dropped: int = Field(..., description="Сколько невалидных телефонов отброшено")

class SyncResultResponse(BaseModel):
    clients: List[ClientResponse]
    stats: StatsResponse
