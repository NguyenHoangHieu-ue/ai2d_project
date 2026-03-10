from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class MetaData(BaseModel):
    category: Optional[str] = None
    domain: Optional[str] = None
    description: Optional[str] = None

class DiagramItem(BaseModel):
    id: str
    image_url: str
    meta: MetaData
    graph: Optional[Dict[str, Any]] = None
    raw_data: Optional[Any] = None

class DiagramListResponse(BaseModel):
    total: int
    items: List[DiagramItem]

class DiagramDetailResponse(BaseModel):
    id: str
    image_url: str
    meta: MetaData
    graph: Optional[Dict[str, Any]] = None
    raw_data: Optional[Dict[str, Any]] = None

class SearchItem(BaseModel):
    id: str
    image_url: str
    meta: MetaData

class SearchResponse(BaseModel):
    total: int
    items: List[SearchItem]