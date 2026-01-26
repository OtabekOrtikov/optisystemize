from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class ExtractedDoc(BaseModel):
    doc_type: Literal["receipt", "invoice", "statement", "other"] = Field(..., description="Type of the document")
    doc_date: Optional[str] = Field(None, description="ISO format YYYY-MM-DD. Null if not visible.")
    merchant: Optional[str] = Field(None, description="Name of the merchant or sender.")
    total_amount: Optional[float] = Field(None, description="Total amount paid/due.")
    currency: Optional[str] = Field(None, description="Currency code (e.g., USD, UZS, EUR).")
    payment_method: Optional[str] = Field(None, description="Cash, Card, Transfer, etc.")
    notes: Optional[str] = Field(None, description="Brief summary or visible notes.")
    confidence: float = Field(..., description="Confidence score 0.0 to 1.0")
    uncertain_fields: List[str] = Field(default_factory=list, description="List of fields where extraction was unsure.")
    language_hint: Optional[str] = Field(None, description="Language of the document.")

class ManifestEntry(BaseModel):
    ts: str
    event: str
    hash: str
    src: str
    kind: str
    status: str
    dst: Optional[str] = None
    error: Optional[str] = None
    duplicate_of: Optional[str] = None