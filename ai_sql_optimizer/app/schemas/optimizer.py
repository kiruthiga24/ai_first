from pydantic import BaseModel
from typing import Optional, Any

class OptimizeRequest(BaseModel):
    sql: str
    table: Optional[str] = None

class OptimizeResponse(BaseModel):
    original_sql: str
    optimized_sql: str
    diff: Optional[str]
    stats_before: Optional[Any]
    stats_after: Optional[Any]
