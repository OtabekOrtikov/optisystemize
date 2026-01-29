from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class FileStatus(str, Enum):
    NEW = "new"
    EXTRACTED = "extracted"
    ERROR = "error"
    ORGANIZED = "organized"
    SKIPPED = "skipped"

class ManifestEntry(BaseModel):
    ts: str = Field(default_factory=lambda: datetime.now().isoformat())
    event: str  # ingest, extract, organize
    hash: str
    src: str
    kind: str = "file"
    status: str
    details: Optional[Dict[str, Any]] = None
    dst: Optional[str] = None

class ExtractedData(BaseModel):
    doc_type: str = Field(description="One of: Receipt, Invoice, Statement, Contract, Other")
    doc_date: Optional[str] = Field(description="YYYY-MM-DD format if found")
    merchant: Optional[str] = Field(description="Name of vendor/sender")
    total_amount: Optional[float] = Field(description="Total amount")
    currency: Optional[str] = Field(description="Currency code: USD, UZS, EUR, RUB, etc.")
    summary: Optional[str] = Field(description="Brief summary of content")
    lines: Optional[List[Dict[str, Any]]] = Field(description="Line items if applicable", default=[])
    
    # Meta
    confidence: float = Field(default=0.0, description="Confidence score 0.0-1.0")
    uncertain_fields: List[str] = Field(default=[], description="List of fields with low confidence")
    is_review_needed: bool = Field(default=False)
