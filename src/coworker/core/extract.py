import json
import asyncio
import io
import time
from pathlib import Path
from typing import Optional, List
from google import genai
from google.genai import types
from pydantic import ValidationError
from PIL import Image, ImageEnhance

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
                parts = []
                
                # Image Preprocessing (simple contrast enhancement)
                if file_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}:
                    try:
                        with Image.open(file_path) as img:
                            # 1. Original
                            img_byte_arr = io.BytesIO()
                            img.save(img_byte_arr, format=img.format)
                            parts.append(types.Part.from_bytes(
                                data=img_byte_arr.getvalue(), 
                                mime_type=f"image/{img.format.lower()}"
                            ))
                            
                            # 2. Contrast Enhanced (if user requested "variants")
                            # We send both to give Gemini "better vision"
                            enhancer = ImageEnhance.Contrast(img)
                            img_contrast = enhancer.enhance(1.5)
                            img_byte_arr_c = io.BytesIO()
                            img_contrast.save(img_byte_arr_c, format=img.format)
                            parts.append(types.Part.from_bytes(
                                data=img_byte_arr_c.getvalue(), 
                                mime_type=f"image/{img.format.lower()}"
                            ))
                    except Exception as e:
                        # Fallback to simple read if PIL fails
                        with open(file_path, "rb") as f:
                             parts.append(types.Part.from_bytes(data=f.read(), mime_type="image/jpeg"))
                
                elif file_path.suffix.lower() == '.pdf':
                     with open(file_path, "rb") as f:
                        parts.append(types.Part.from_bytes(data=f.read(), mime_type="application/pdf"))
                
                else:
                    return None # Unsupported

                # Generate sanitized schema
                schema = ExtractedData.model_json_schema()
                def strip_schema(s):
                    if isinstance(s, dict):
                        # Remove forbidden/internal keys
                        s.pop('additionalProperties', None)
                        s.pop('title', None)
                        
                        # Remove specific properties we don't want LLM to worry about
                        props = s.get('properties', {})
                        if isinstance(props, dict):
                            props.pop('token_usage', None)
                            props.pop('processing_time', None)
                            
                        # Recurse
                        for v in s.values():
                            strip_schema(v)
                    elif isinstance(s, list):
                        for i in s:
                            strip_schema(i)
                strip_schema(schema)

                start_time = asyncio.get_event_loop().time()
                response = await self.client.aio.models.generate_content(
                    model=settings.MODEL_NAME,
                    contents=parts + [PROMPT],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema
                    )
                )
                end_time = asyncio.get_event_loop().time()
                duration = end_time - start_time
                
                # Extract usage metadata
                usage = {}
                if response.usage_metadata:
                    usage = {
                        "prompt_tokens": response.usage_metadata.prompt_token_count,
                        "candidates_tokens": response.usage_metadata.candidates_token_count,
                        "total_tokens": response.usage_metadata.total_token_count
                    }
                
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
                        is_review_needed=True,
                        review_reason="Parse Error"
                    )

                extracted.processing_time = duration
                extracted.token_usage = usage

                # Post-process confidence & Review Logic
                reasons = []
                if not extracted.doc_date: reasons.append("Missing Date")
                if not extracted.total_amount: reasons.append("Missing Amount")
                
                if reasons:
                    extracted.confidence = min(extracted.confidence, 0.6)
                    extracted.is_review_needed = True
                    extracted.review_reason = ", ".join(reasons)
                
                if extracted.confidence < 0.7:
                    extracted.is_review_needed = True
                    if not extracted.review_reason:
                        extracted.review_reason = "Low Confidence"

                # Save cache
                with open(cache_path, 'w') as f:
                    f.write(extracted.model_dump_json(indent=2))

                return extracted

            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")
                return None
