from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr

class FileStatus(str, Enum):
    NEW = "new"
    EXTRACTED = "extracted"
    ERROR = "error"
    ORGANIZED = "organized"
    SKIPPED = "skipped"

class OrganizationMode(str, Enum):
    FOLDERS = "folders"
    EXCEL = "excel"
    BOTH = "both"

class CategoriesMode(str, Enum):
    AUTO = "auto"
    BUSINESS = "business"
    PERSONAL = "personal"
    CUSTOM = "custom"

class Config(BaseModel):
    lang: Optional[str] = None # ru or en
    organization_mode: OrganizationMode = OrganizationMode.BOTH
    categories_mode: CategoriesMode = CategoriesMode.AUTO
    max_categories: int = 12
    custom_categories: List[str] = []

class ManifestEntry(BaseModel):
    ts: str = Field(default_factory=lambda: datetime.now().isoformat())
    event: str  # ingest, extract, organize
    hash: str
    src: str
    kind: str = "file"
    status: str
    details: Optional[Dict[str, Any]] = None
    dst: Optional[str] = None

class LineItem(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None
    qty: Optional[float] = None

class ExtractedData(BaseModel):
    doc_type: str = Field(description="One of: Receipt, Invoice, Statement, Contract, Other")
    doc_date: Optional[str] = Field(default=None, description="YYYY-MM-DD format if found")
    merchant: Optional[str] = Field(default=None, description="Name of vendor/sender")
    total_amount: Optional[float] = Field(default=None, description="Total amount")
    currency: Optional[str] = Field(default=None, description="Currency code: USD, UZS, EUR, RUB, etc.")
    summary: Optional[str] = Field(default=None, description="Brief summary of content")
    lines: Optional[List[LineItem]] = Field(description="Line items if applicable", default=[])
    
    # Meta
    confidence: float = Field(default=0.0, description="Confidence score 0.0-1.0")
    uncertain_fields: List[str] = Field(default=[], description="List of fields with low confidence")
    is_review_needed: bool = Field(default=False)
    review_reason: Optional[str] = None
    
    # Metrics
    processing_time: float = Field(default=0.0, description="Time taken to process in seconds")
    token_usage: Dict[str, int] = Field(default_factory=dict, description="Token usage details")
    
    _is_cached: bool = PrivateAttr(default=False)

    model_config = ConfigDict(extra='forbid')
