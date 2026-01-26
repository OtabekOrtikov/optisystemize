import json
import os
from pathlib import Path
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv

from terminal_coworker.models import ExtractedDoc
from terminal_coworker.utils import preprocess_image

load_dotenv()

SYSTEM_INSTRUCTION = """
You are a document extraction assistant. 
Analyze the provided image(s) of a receipt, invoice, or statement.
Extract data strictly according to the JSON schema.
Rules:
1. If a date is ambiguous, look for the transaction date. format YYYY-MM-DD.
2. If total amount is unclear, use the largest logical sum.
3. If fields are not visible/readable, set them to null and add field name to 'uncertain_fields'.
4. Do NOT guess. If unsure, lower the confidence score.
5. If the document is not a receipt/invoice (e.g. a cat photo), set doc_type='other' and confidence=1.0.
"""

def extract_data(file_path: Path, file_hash: str, project_path: Path, force: bool = False) -> ExtractedDoc:
    cache_path = project_path / "cache" / f"{file_hash}.json"
    
    # Check cache
    if cache_path.exists() and not force:
        with open(cache_path, "r", encoding="utf-8") as f:
            return ExtractedDoc(**json.load(f))

    # Determine file type
    suffix = file_path.suffix.lower()
    if suffix not in ['.jpg', '.jpeg', '.png', '.webp', '.pdf']:
        # Skip non-visual files for now or implement text parsers
        return None

    # Init Client
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    # Prepare Content
    inputs = []
    if suffix == '.pdf':
        with open(file_path, "rb") as f:
            inputs.append(types.Part.from_bytes(data=f.read(), mime_type="application/pdf"))
    else:
        # Image preprocessing
        images = preprocess_image(file_path)
        for img in images:
             inputs.append(img)
    
    if not inputs:
        return None

    # Call Gemini
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash", # Or gemini-1.5-flash
            contents=inputs,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=ExtractedDoc
            )
        )
        
        extracted_data = response.parsed # Pydantic object
        
        # Save to Cache
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(extracted_data.model_dump_json(indent=2))
            
        return extracted_data

    except Exception as e:
        print(f"Error extracting {file_path.name}: {e}")
        return None