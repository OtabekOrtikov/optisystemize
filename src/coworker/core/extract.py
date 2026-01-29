import json
import base64
import asyncio
from pathlib import Path
from typing import Optional
from google import genai
from google.genai import types
from pydantic import ValidationError

from .config import settings
from .models import ExtractedData

PROMPT = """
You are an expert document extraction AI. Analyze this document (receipt, invoice, bank statement, or other).
Extract the following information into a strict JSON format:
- doc_type: One of 'Receipt', 'Invoice', 'Statement', 'Contract', 'Other'
- doc_date: Date of the document in YYYY-MM-DD format. If ambiguous, use the most likely date.
- merchant: The name of the vendor, sender, or entity issuing the document.
- total_amount: The total numeric amount (float).
- currency: The currency code (e.g., USD, UZS, EUR, RUB).
- summary: A brief 1-sentence summary of what this document is.
- lines: Array of line items (description, amount) if clearly visible.

Analyze the confidence of your extraction (0.0 to 1.0).
If key fields (date, amount, currency) are missing or unclear, lower the confidence.
List any uncertain fields in 'uncertain_fields'.
If the document is unreadable or not a document, set doc_type to 'Other' and confidence to 0.

Return ONLY the JSON.
"""

class Extractor:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.semaphore = asyncio.Semaphore(settings.CONCURRENCY)

    async def extract_file(self, file_path: Path, cache_path: Path, force: bool = False) -> Optional[ExtractedData]:
        # Check cache
        if not force and cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                return ExtractedData(**data)
            except Exception:
                pass # Invalid cache, re-process

        async with self.semaphore:
            try:
                # Prepare content
                if file_path.suffix.lower() == '.pdf':
                    with open(file_path, "rb") as f:
                        file_content = f.read()
                    part = types.Part.from_bytes(data=file_content, mime_type="application/pdf")
                else:
                    with open(file_path, "rb") as f:
                        file_content = f.read()
                    part = types.Part.from_bytes(data=file_content, mime_type="image/jpeg") # Generically use jpeg for images

                response = await self.client.aio.models.generate_content(
                    model=settings.MODEL_NAME,
                    contents=[part, PROMPT],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ExtractedData
                    )
                )
                
                if not response.text:
                    return None

                # Parse and validate
                try:
                    data = json.loads(response.text)
                    extracted = ExtractedData(**data)
                except (json.JSONDecodeError, ValidationError):
                    # Fallback or error
                    extracted = ExtractedData(
                        doc_type="Other",
                        summary="Extraction failed to parse",
                        confidence=0.0,
                        uncertain_fields=["all"],
                        is_review_needed=True
                    )

                # Post-process confidence
                if not extracted.doc_date or not extracted.total_amount:
                   extracted.confidence = min(extracted.confidence, 0.6)
                   extracted.is_review_needed = True
                
                if extracted.confidence < 0.7:
                    extracted.is_review_needed = True

                # Save cache
                with open(cache_path, 'w') as f:
                    f.write(extracted.model_dump_json(indent=2))

                return extracted

            except Exception as e:
                # Log error (print for now or use logging)
                print(f"Error processing {file_path.name}: {e}")
                return None
