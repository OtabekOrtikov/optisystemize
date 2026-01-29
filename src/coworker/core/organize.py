import shutil
import re
from pathlib import Path
from typing import Dict, Any, List, Counter

from .models import ExtractedData, FileStatus, OrganizationMode, CategoriesMode
from .storage import Workspace
from .config import settings

def sanitize_filename(name: str) -> str:
    # Remove invalid chars
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.strip().replace(' ', '_')
    return name[:50]  # Limit length

def get_target_category(doc_type: str, all_categories: Counter, max_categories: int) -> str:
    # Use categories from extraction, but we can enforce limits here if needed.
    # For now, just pass through unless custom logic is requested.
    return doc_type

def organize_file(
    src_path: Path, 
    data: ExtractedData, 
    workspace: Workspace,
    f_hash: str,
    dry_run: bool = False,
    mode: str = "copy"
) -> Dict[str, Any]:
    
    # 1. Determine Category
    category = data.doc_type
    
    # Apply logic based on config settings.config.categories_mode if needed
    # e.g. mapping "Receipt" to "Business" if mode is BUSINESS
    # For "Auto", we stick to Gemini's determination.
    
    # 2. Determine Destination
    if data.is_review_needed:
        # To Review
        dest_folder = workspace.review
        reason = data.review_reason or "Review"
        # Sanitize reason for folder name
        reason_folder = sanitize_filename(reason)
        target_dir = dest_folder / reason_folder
    else:
        # To Organized
        date_folder = "Unknown_Date"
        if data.doc_date:
            try:
                date_folder = data.doc_date[:7] # YYYY-MM
            except: pass
        
        target_dir = workspace.organized / date_folder / category

    # 3. Naming Convention
    # <YYYY-MM-DD>__<Category>__<Merchant>__<Amount><Currency>__<hash>.<ext>
    ext = src_path.suffix
    
    parts = []
    parts.append(data.doc_date if data.doc_date else "Unknown")
    parts.append(category)
    parts.append(sanitize_filename(data.merchant) if data.merchant else "Unknown")
    
    amt = f"{data.total_amount}" if data.total_amount else "0"
    curr = data.currency if data.currency else ""
    parts.append(f"{amt}{curr}")
    
    # Add short hash to ensure uniqueness and traceability
    short_hash = f_hash[:8]
    parts.append(short_hash)
    
    base_name = "__".join(parts)
    new_name = f"{base_name}{ext}"

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Collision handling
        dest_path = target_dir / new_name
        counter = 1
        while dest_path.exists():
             dest_path = target_dir / f"{base_name}_{counter}{ext}"
             counter += 1
             
        if mode == "move":
            shutil.move(src_path, dest_path)
        else:
            shutil.copy2(src_path, dest_path)
        return {
            "status": FileStatus.ORGANIZED,
            "dst": str(dest_path)
        }
    else:
        return {
            "status": FileStatus.SKIPPED,
            "dst": "dry-run"
        }
